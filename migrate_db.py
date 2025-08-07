#!/usr/bin/env python3
"""
Migration script to update PostgreSQL database schema
"""
import os
from dotenv import load_dotenv
from config import get_database_uri
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

def migrate_database():
    """Migrate database schema for PostgreSQL compatibility"""
    
    database_uri = get_database_uri()
    print(f"Connecting to database: {database_uri}")
    
    # Create engine
    engine = create_engine(database_uri)
    
    try:
        with engine.connect() as connection:
            print("Connected to database successfully!")
            
            # Begin transaction
            trans = connection.begin()
            
            try:
                # Check if password column exists and its length
                result = connection.execute(text("""
                    SELECT character_maximum_length 
                    FROM information_schema.columns 
                    WHERE table_name = 'user' AND column_name = 'password'
                """)).fetchone()
                
                if result:
                    current_length = result[0]
                    print(f"Current password column length: {current_length}")
                    
                    if current_length and current_length < 255:
                        print("Updating password column to VARCHAR(255)...")
                        connection.execute(text("""
                            ALTER TABLE "user" 
                            ALTER COLUMN password TYPE VARCHAR(255)
                        """))
                        print("✅ Password column updated successfully!")
                    else:
                        print("✅ Password column already has sufficient length")
                else:
                    print("❌ User table or password column not found")
                
                # Commit transaction
                trans.commit()
                print("✅ Migration completed successfully!")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Migration failed: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    migrate_database()
