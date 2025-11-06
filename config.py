import os

class Config:
    # Количество строк для вывода в табличном представлении
    TABLE_ROWS_PER_PAGE = 3
    
    # Настройки автодополнения
    AUTOCOMPLETE_MIN_CHARS = 3
    AUTOCOMPLETE_LIMIT = 10
    
    # Настройки мозаики для блочного представления
    GRID_COLUMNS = 3  # Количество колонок в мозаике