#!/usr/bin/env python
"""Clear all data from the SQLite database while preserving schema."""

import sqlite3
import os
import sys

def clear_database():
    """Delete all records from users and resumes tables."""
    db_path = os.path.join(os.getcwd(), 'instance', 'app.db')
    
    if not os.path.exists(db_path):
        print('❌ Database file not found at:', db_path)
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get counts before deletion
        cursor.execute('SELECT COUNT(*) FROM resumes')
        resume_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        # Delete all data
        cursor.execute('DELETE FROM resumes')
        cursor.execute('DELETE FROM users')
        conn.commit()
        
        print('✓ Database cleared successfully!')
        print(f'\nDeleted:')
        print(f'  - {resume_count} resume record(s)')
        print(f'  - {user_count} user record(s)')
        print(f'\nDatabase: {db_path}')
        print('Schema: Preserved')
        
        conn.close()
        return True
        
    except Exception as e:
        print(f'❌ Error clearing database: {str(e)}')
        return False

if __name__ == '__main__':
    success = clear_database()
    sys.exit(0 if success else 1)
