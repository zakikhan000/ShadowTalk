from fastapi import FastAPI, HTTPException, Request
import pymssql
from pydantic import BaseModel, create_model
from typing import Dict, Any, List, Tuple, Type, Optional
import base64
import logging

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)

# Database configuration (adjust as necessary)
DB_USER = "zaki"
DB_PASSWORD = "12365@Khan"
DB_SERVER = "sqlserverfyp.database.windows.net"
DB_DATABASE = "WeShareDB"
DB_PORT = 1433


def get_db_connection():
    try:
        conn = pymssql.connect(
            server=DB_SERVER,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_DATABASE,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        logging.error(f"Database connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# Mapping of each table to its primary key column
tables = {
    "ChatbotMessages": "chat_id",
    "Comments": "comment_id",
    "Likes": "like_id",
    "MentalHealthAnalysis": "record_id",
    "Messages": "message_id",
    "Notifications": "notification_id",
    "Posts": "post_id",
    "SentimentAnalysis": "analysis_id",
    "UserInterests": "interest_id",
    "Users": "user_id"
}

# List of tables that support soft deletion
soft_delete_tables = ["Comments", "Messages", "Posts", "Users"]

# ----------------------------------------------------------------------
# DYNAMIC MODEL GENERATION (same as before)
# ----------------------------------------------------------------------
def sql_type_to_python_type(sql_type: str) -> Type:
    sql_type = sql_type.lower()
    if "int" in sql_type:
        return Optional[int]
    elif "decimal" in sql_type or "numeric" in sql_type or "money" in sql_type:
        return Optional[float]
    elif "float" in sql_type or "real" in sql_type:
        return Optional[float]
    elif "bit" in sql_type or "bool" in sql_type:
        return Optional[bool]
    elif "char" in sql_type or "text" in sql_type:
        return Optional[str]
    elif "date" in sql_type or "time" in sql_type:
        return Optional[str]
    elif "binary" in sql_type or "image" in sql_type:
        return Optional[bytes]
    else:
        return Optional[str]

def get_table_columns(table_name: str) -> List[Tuple[str, str]]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        cursor.execute(query, (table_name,))
        columns = cursor.fetchall()
        return columns
    except Exception as e:
        logging.error(f"Error getting columns for {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

def create_pydantic_model_for_table(table_name: str) -> Type[BaseModel]:
    columns = get_table_columns(table_name)
    model_fields = {}
    for col_name, data_type in columns:
        python_type = sql_type_to_python_type(data_type)
        model_fields[col_name] = (python_type, None)
    model = create_model(f"{table_name}Model", **model_fields)
    return model

table_models: Dict[str, Type[BaseModel]] = {}
for table_name in tables.keys():
    table_models[table_name] = create_pydantic_model_for_table(table_name)

def clean_users_record(record: Dict[str, Any]) -> Dict[str, Any]:
    if "profile_image" in record and record["profile_image"]:
        try:
            record["profile_image"] = base64.b64encode(record["profile_image"]).decode('utf-8')
        except Exception as e:
            logging.error(f"Error encoding profile image: {str(e)}")
            record["profile_image"] = ""
    return record

# ----------------------------------------------------------------------
# CRUD Endpoint Factories (get, post, put, delete) – same as before
# ----------------------------------------------------------------------
def create_get_all_endpoint(table_name: str, pk_name: str):
    async def get_all_records():
        conn = get_db_connection()
        try:
            cursor = conn.cursor(as_dict=True)
            if table_name in soft_delete_tables:
                query = f"SELECT * FROM {table_name} WHERE is_deleted = 0"
            else:
                query = f"SELECT * FROM {table_name}"
            cursor.execute(query)
            records = cursor.fetchall()
            if table_name == "Users":
                records = [clean_users_record(r) for r in records]
            return records
        except Exception as e:
            logging.error(f"Error in get_all_records for {table_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()
    return get_all_records

def create_get_one_endpoint(table_name: str, pk_name: str):
    async def get_record_by_id(id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor(as_dict=True)
            if table_name in soft_delete_tables:
                query = f"SELECT * FROM {table_name} WHERE {pk_name} = %s AND is_deleted = 0"
            else:
                query = f"SELECT * FROM {table_name} WHERE {pk_name} = %s"
            cursor.execute(query, (id,))
            record = cursor.fetchone()
            if not record:
                raise HTTPException(status_code=404, detail="Record not found")
            if table_name == "Users":
                record = clean_users_record(record)
            return record
        except Exception as e:
            logging.error(f"Error in get_record_by_id for {table_name}: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()
    return get_record_by_id

def create_post_endpoint(table_name: str, pk_name: str, model: Type[BaseModel]):
    async def insert_record(data: model):
        data_dict = data.dict(exclude_unset=True)
        if not data_dict:
            raise HTTPException(status_code=400, detail="No fields provided for insertion")
        if pk_name in data_dict:
            data_dict.pop(pk_name)
        if table_name == "Users" and "profile_image" in data_dict and data_dict["profile_image"]:
            try:
                data_dict["profile_image"] = base64.b64decode(data_dict["profile_image"])
            except Exception as e:
                raise HTTPException(status_code=400, detail="Invalid base64 for profile_image: " + str(e))
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            columns = ", ".join(data_dict.keys())
            placeholders = ", ".join(["%s"] * len(data_dict))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            cursor.execute(query, tuple(data_dict.values()))
            conn.commit()
            return {"message": "Record inserted successfully"}
        except Exception as e:
            conn.rollback()
            logging.error(f"Error inserting record into {table_name}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error inserting record into " + table_name + ": " + str(e))
        finally:
            conn.close()
    return insert_record

def create_put_endpoint(table_name: str, pk_name: str, model: Type[BaseModel]):
    async def update_record(id: int, data: model):
        data_dict = data.dict(exclude_unset=True)
        if not data_dict:
            raise HTTPException(status_code=400, detail="No fields provided for update")
        if pk_name in data_dict:
            data_dict.pop(pk_name)
        if table_name == "Users" and "profile_image" in data_dict and data_dict["profile_image"]:
            try:
                data_dict["profile_image"] = base64.b64decode(data_dict["profile_image"])
            except Exception as e:
                raise HTTPException(status_code=400, detail="Invalid base64 for profile_image: " + str(e))
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            updates = ", ".join([f"{col} = %s" for col in data_dict.keys()])
            query = f"UPDATE {table_name} SET {updates} WHERE {pk_name} = %s"
            cursor.execute(query, tuple(data_dict.values()) + (id,))
            conn.commit()
            return {"message": "Record updated successfully"}
        except Exception as e:
            conn.rollback()
            logging.error(f"Error updating record in {table_name}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error updating record in " + table_name + ": " + str(e))
        finally:
            conn.close()
    return update_record

def create_delete_endpoint(table_name: str, pk_name: str):
    async def delete_record(id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if table_name in soft_delete_tables:
                query = f"UPDATE {table_name} SET is_deleted = 1 WHERE {pk_name} = %s"
                cursor.execute(query, (id,))
            else:
                query = f"DELETE FROM {table_name} WHERE {pk_name} = %s"
                cursor.execute(query, (id,))
            conn.commit()
            return {"message": "Record deleted successfully"}
        except Exception as e:
            conn.rollback()
            logging.error(f"Error deleting record from {table_name}: {str(e)}")
            raise HTTPException(status_code=500, detail="Error deleting record from " + table_name + ": " + str(e))
        finally:
            conn.close()
    return delete_record

# ----------------------------------------------------------------------
# REGISTER ALL ROUTES DYNAMICALLY
# ----------------------------------------------------------------------
for table_name, pk_name in tables.items():
    model_class = table_models[table_name]

    app.add_api_route(
        f"/api/{table_name}",
        create_get_all_endpoint(table_name, pk_name),
        methods=["GET"],
        name=f"Get all {table_name}",
    )

    app.add_api_route(
        f"/api/{table_name}/{{id}}",
        create_get_one_endpoint(table_name, pk_name),
        methods=["GET"],
        name=f"Get {table_name} by ID",
    )

    app.add_api_route(
        f"/api/{table_name}",
        create_post_endpoint(table_name, pk_name, model_class),
        methods=["POST"],
        name=f"Insert record into {table_name}",
    )

    app.add_api_route(
        f"/api/{table_name}/{{id}}",
        create_put_endpoint(table_name, pk_name, model_class),
        methods=["PUT"],
        name=f"Update record in {table_name}",
    )

    app.add_api_route(
        f"/api/{table_name}/{{id}}",
        create_delete_endpoint(table_name, pk_name),
        methods=["DELETE"],
        name=f"Delete record from {table_name}",
    )

# ----------------------------------------------------------------------
# ALL-DATA ENDPOINT
# ----------------------------------------------------------------------
@app.get("/api/all-data")
async def get_all_data():
    conn = get_db_connection()
    all_data = {}
    try:
        for table_name in tables.keys():
            cursor = conn.cursor(as_dict=True)
            if table_name in soft_delete_tables:
                query = f"SELECT * FROM {table_name} WHERE is_deleted = 0"
            else:
                query = f"SELECT * FROM {table_name}"
            cursor.execute(query)
            rows = cursor.fetchall()
            if table_name == "Users":
                rows = [clean_users_record(row) for row in rows]
            all_data[table_name] = rows if rows else []
        return all_data
    except Exception as e:
        logging.error(f"Error in all-data endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ----------------------------------------------------------------------
# TABLE FIELDS ENDPOINT
# ----------------------------------------------------------------------
@app.get("/api/fields/{table_name}")
async def get_table_fields(table_name: str):
    if table_name not in tables:
        raise HTTPException(status_code=400, detail="Invalid table name.")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        cursor.execute(query, (table_name,))
        columns = cursor.fetchall()
        result = [{"column_name": row[0], "data_type": row[1]} for row in columns]
        return result
    except Exception as e:
        logging.error(f"Error getting fields for {table_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ----------------------------------------------------------------------
# LOGIN ENDPOINT – accepts login (email, username or phone) and password
# ----------------------------------------------------------------------
class LoginModel(BaseModel):
    login: str
    password: str

@app.post("/api/login")
async def login(credentials: LoginModel):
    conn = get_db_connection()
    try:
        cursor = conn.cursor(as_dict=True)
        query = """
            SELECT * FROM Users 
            WHERE (email = %s OR username = %s OR phone_number = %s) 
              AND password_hash = %s 
              AND is_deleted = 0
        """
        cursor.execute(query, (credentials.login, credentials.login, credentials.login, credentials.password))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid login credentials")
        user = clean_users_record(user)
        return {"message": "Login successful", "user": user}
    except Exception as e:
        logging.error(f"Login failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed: " + str(e))
    finally:
        conn.close()

# ----------------------------------------------------------------------
# APP ENTRY POINT
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
