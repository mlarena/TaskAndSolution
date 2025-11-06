import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# Database configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'problem_tracker'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '12345678'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/problems')
def problems():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all problems with their tags
    cur.execute('''
        SELECT p.*, array_agg(t.name) as tag_names
        FROM problems p
        LEFT JOIN problem_tags pt ON p.id = pt.problem_id
        LEFT JOIN tags t ON pt.tag_id = t.id
        GROUP BY p.id
        ORDER BY p.created_at DESC
    ''')
    problems = cur.fetchall()
    
    # Get all tags for the form
    cur.execute('SELECT * FROM tags ORDER BY name')
    tags = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('problems.html', problems=problems, tags=tags)

@app.route('/problem/new', methods=['GET', 'POST'])
def new_problem():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        solution = request.form['solution']
        selected_tags = request.form.getlist('tags')
        new_tags = request.form.get('new_tags', '').split(',')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            # Insert problem
            cur.execute(
                'INSERT INTO problems (title, description, solution) VALUES (%s, %s, %s) RETURNING id',
                (title, description, solution)
            )
            problem_id = cur.fetchone()[0]
            
            # Process existing tags
            for tag_id in selected_tags:
                if tag_id:
                    cur.execute(
                        'INSERT INTO problem_tags (problem_id, tag_id) VALUES (%s, %s)',
                        (problem_id, tag_id)
                    )
            
            # Process new tags
            for tag_name in new_tags:
                tag_name = tag_name.strip()
                if tag_name:
                    # Insert new tag
                    cur.execute(
                        'INSERT INTO tags (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id',
                        (tag_name,)
                    )
                    result = cur.fetchone()
                    if result:
                        tag_id = result[0]
                    else:
                        # If tag already exists, get its ID
                        cur.execute('SELECT id FROM tags WHERE name = %s', (tag_name,))
                        tag_id = cur.fetchone()[0]
                    
                    # Link tag to problem
                    cur.execute(
                        'INSERT INTO problem_tags (problem_id, tag_id) VALUES (%s, %s)',
                        (problem_id, tag_id)
                    )
            
            conn.commit()
            flash('Problem created successfully!', 'success')
            
        except Exception as e:
            conn.rollback()
            flash(f'Error creating problem: {str(e)}', 'error')
        finally:
            cur.close()
            conn.close()
        
        return redirect(url_for('problems'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('SELECT * FROM tags ORDER BY name')
    tags = cur.fetchall()
    cur.close()
    conn.close()
    
    return render_template('problem_form.html', tags=tags, problem=None)

@app.route('/problem/<int:problem_id>/edit', methods=['GET', 'POST'])
def edit_problem(problem_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        solution = request.form['solution']
        selected_tags = request.form.getlist('tags')
        new_tags = request.form.get('new_tags', '').split(',')
        
        try:
            # Update problem
            cur.execute(
                'UPDATE problems SET title = %s, description = %s, solution = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s',
                (title, description, solution, problem_id)
            )
            
            # Remove existing tags
            cur.execute('DELETE FROM problem_tags WHERE problem_id = %s', (problem_id,))
            
            # Process existing tags
            for tag_id in selected_tags:
                if tag_id:
                    cur.execute(
                        'INSERT INTO problem_tags (problem_id, tag_id) VALUES (%s, %s)',
                        (problem_id, tag_id)
                    )
            
            # Process new tags
            for tag_name in new_tags:
                tag_name = tag_name.strip()
                if tag_name:
                    # Insert new tag
                    cur.execute(
                        'INSERT INTO tags (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id',
                        (tag_name,)
                    )
                    result = cur.fetchone()
                    if result:
                        tag_id = result[0]
                    else:
                        cur.execute('SELECT id FROM tags WHERE name = %s', (tag_name,))
                        tag_id = cur.fetchone()[0]
                    
                    cur.execute(
                        'INSERT INTO problem_tags (problem_id, tag_id) VALUES (%s, %s)',
                        (problem_id, tag_id)
                    )
            
            conn.commit()
            flash('Problem updated successfully!', 'success')
            
        except Exception as e:
            conn.rollback()
            flash(f'Error updating problem: {str(e)}', 'error')
        finally:
            cur.close()
            conn.close()
        
        return redirect(url_for('problems'))
    
    # Get problem data for editing
    cur.execute('SELECT * FROM problems WHERE id = %s', (problem_id,))
    problem = cur.fetchone()
    
    cur.execute('''
        SELECT t.id, t.name 
        FROM tags t 
        JOIN problem_tags pt ON t.id = pt.tag_id 
        WHERE pt.problem_id = %s
    ''', (problem_id,))
    problem_tags = [tag['id'] for tag in cur.fetchall()]
    
    cur.execute('SELECT * FROM tags ORDER BY name')
    all_tags = cur.fetchall()
    
    cur.close()
    conn.close()
    
    if not problem:
        flash('Problem not found!', 'error')
        return redirect(url_for('problems'))
    
    return render_template('problem_form.html', problem=problem, tags=all_tags, problem_tags=problem_tags)

@app.route('/problem/<int:problem_id>/delete', methods=['POST'])
def delete_problem(problem_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # First delete from problem_tags (due to foreign key constraint)
        cur.execute('DELETE FROM problem_tags WHERE problem_id = %s', (problem_id,))
        # Then delete the problem
        cur.execute('DELETE FROM problems WHERE id = %s', (problem_id,))
        conn.commit()
        flash('Problem deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting problem: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('problems'))

@app.route('/tags')
def tags():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute('''
        SELECT t.*, COUNT(pt.problem_id) as usage_count
        FROM tags t
        LEFT JOIN problem_tags pt ON t.id = pt.tag_id
        GROUP BY t.id
        ORDER BY t.name
    ''')
    tags = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('tags.html', tags=tags)

@app.route('/tag/<int:tag_id>/delete', methods=['POST'])
def delete_tag(tag_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # First delete from problem_tags
        cur.execute('DELETE FROM problem_tags WHERE tag_id = %s', (tag_id,))
        # Then delete the tag
        cur.execute('DELETE FROM tags WHERE id = %s', (tag_id,))
        conn.commit()
        flash('Tag deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting tag: {str(e)}', 'error')
    finally:
        cur.close()
        conn.close()
    
    return redirect(url_for('tags'))


@app.route('/problem/<int:problem_id>')
def view_problem(problem_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get problem with tags
    cur.execute('''
        SELECT p.*, array_agg(t.name) as tag_names
        FROM problems p
        LEFT JOIN problem_tags pt ON p.id = pt.problem_id
        LEFT JOIN tags t ON pt.tag_id = t.id
        WHERE p.id = %s
        GROUP BY p.id
    ''', (problem_id,))
    
    problem = cur.fetchone()
    cur.close()
    conn.close()
    
    if not problem:
        flash('Problem not found!', 'error')
        return redirect(url_for('problems'))
    
    return render_template('problem_detail.html', problem=problem)


if __name__ == '__main__':
    app.run(debug=True)