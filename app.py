import os
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv
import psycopg2
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

def get_db_connection():
    conn = psycopg2.connect(
        host='localhost',
        database='problem_tracker',
        user='postgres',
        password='12345678'
    )
    return conn

@app.route('/problems')
def problems():
    view_type = request.args.get('view', 'table')  # table или grid
    page = request.args.get('page', 1, type=int)
    search_term = request.args.get('search', '')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Базовый запрос
    query = "SELECT * FROM problems WHERE 1=1"
    params = []
    
    # Применяем поиск если есть термин
    if search_term:
        query += " AND (title ILIKE %s OR problem ILIKE %s OR solution ILIKE %s)"
        search_pattern = f"%{search_term}%"
        params.extend([search_pattern, search_pattern, search_pattern])
    
    # Для табличного представления - пагинация
    if view_type == 'table':
        limit = app.config['TABLE_ROWS_PER_PAGE']
        offset = (page - 1) * limit
        query += " ORDER BY id LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cur.execute(query, params)
        problems_data = cur.fetchall()
        
        # Получаем общее количество для пагинации
        count_query = "SELECT COUNT(*) FROM problems"
        if search_term:
            count_query += " WHERE (title ILIKE %s OR problem ILIKE %s OR solution ILIKE %s)"
            cur.execute(count_query, [search_pattern, search_pattern, search_pattern])
        else:
            cur.execute(count_query)
        
        total_count = cur.fetchone()[0]
        total_pages = (total_count + limit - 1) // limit
        
    else:  # grid view - все данные
        query += " ORDER BY id"
        cur.execute(query, params)
        problems_data = cur.fetchall()
        total_pages = 1
    
    cur.close()
    conn.close()
    
    return render_template('problems.html', 
                         problems=problems_data,
                         view_type=view_type,
                         current_page=page,
                         total_pages=total_pages,
                         search_term=search_term)

@app.route('/autocomplete')
def autocomplete():
    term = request.args.get('term', '')
    
    if len(term) < app.config['AUTOCOMPLETE_MIN_CHARS']:
        return jsonify([])
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Ищем в title, problem, solution
    search_pattern = f"{term}%"
    query = """
    SELECT DISTINCT suggestion FROM (
        SELECT title as suggestion FROM problems WHERE title ILIKE %s
        UNION 
        SELECT problem as suggestion FROM problems WHERE problem ILIKE %s
        UNION
        SELECT solution as suggestion FROM problems WHERE solution ILIKE %s
    ) AS suggestions 
    LIMIT %s
    """
    
    cur.execute(query, [search_pattern, search_pattern, search_pattern, 
                       app.config['AUTOCOMPLETE_LIMIT']])
    
    suggestions = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    return jsonify(suggestions)

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