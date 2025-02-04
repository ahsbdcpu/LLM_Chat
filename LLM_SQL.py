from vanna.ollama import Ollama 
from vanna.chromadb.chromadb_vector import ChromaDB_VectorStore
import pandas as pd
import mysql.connector
from flask import Flask, request, jsonify
import json
import re
import os
import random
from flask_cors import CORS
import hashlib
from datetime import datetime

class MyVanna(ChromaDB_VectorStore, Ollama):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        Ollama.__init__(self, config=config)

dbType = {'dbType': 'MySQL'} 

def get_database_schema(): #請根據實際情況修改資料庫連線設定
    schema = {}
    cnx = mysql.connector.connect(user='root', password='password', host='localhost', database='XXX', port=3306)
    cursor = cnx.cursor()
    cursor.execute("SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'test'")
    for table_name, column_name in cursor:
        if table_name not in schema:
            schema[table_name] = []
        schema[table_name].append(column_name)
    cursor.close()
    cnx.close()
    return schema

schema = get_database_schema()
schema_text = json.dumps(schema, ensure_ascii=False, indent=4)

sys_prompt = "請幫忙解讀SQL資料庫並只進行查詢語法跟在最後資料解析使用繁體中文回答SQL查詢語法跟資料表就好。並請使用繁體中文回覆。"

def apply_chat_template(sys_content, question):
    chat = [
        {"role": "system", "content": sys_content},
        {"role": "user", "content": f"請僅用繁體中文回覆以下問題：\n{question}\n\n請直接生成符合要求的 SQL 語句，並請以繁體中文回應所有結果。"}
    ]
    prompt = f"{sys_content}\n\n問題：{question}"
    return prompt

vn = MyVanna(config={
    'model': 'llama3.1:8b',
    'sys_prompt': sys_prompt, 
    'ollama_host': 'http://localhost:12345'} # 請根據實際情況修改 ollama_host
)

def run_sql(sql: str) -> pd.DataFrame:  #請根據實際情況修改資料庫連線設定
    print(f"執行 SQL 查詢: {sql}")
    try:
        cnx = mysql.connector.connect(user='root', password='password', host='localhost', database='XXX', port=3306)
        cursor = cnx.cursor()

        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        print("可用的資料表:")
        for db in tables:
            print(db[0])

        cursor.execute(sql)
        result = cursor.fetchall()
        columns = cursor.column_names
        df = pd.DataFrame(result, columns=columns)

        cursor.close()
        cnx.close()
        
        print("SQL 查詢執行成功。")
        return df
    
    except mysql.connector.Error as err:
        print(f"錯誤: {err}")
        return pd.DataFrame()

vn.run_sql = run_sql
vn.run_sql_is_set = True

sql_history = []
sql_result_hashes = {}
sql_to_json_mapping = {} 

def calculate_hash(data):
    data_string = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(data_string.encode('utf-8')).hexdigest()

DB_FILE = 'chroma.sqlite3'

# 暫存檔案
TEMP_FILES = [
    'chroma.sqlite3',
    'chroma.sqlite3-journal'
]

ddl_list = [
    """
CREATE TABLE REPORT (
    OID TEXT PRIMARY KEY,
    HDNUNUSUALTYPENAME TEXT,
    D1_DEPT TEXT,
    D1_NAME TEXT,
    D1_TITLE TEXT,
    D2_DEVICENAME TEXT,
    D2_LOTNO TEXT,
    D2_LOTQTY TEXT,
    D2_PACKAGETYPE TEXT,
    D2_QTY TEXT,
    D2_QTY_P TEXT,
    D2_RUNCARD TEXT,
    D2_UNUSUALTYPE TEXT,
    D2_WHAT TEXT,
    D2_WHEN TEXT,
    D2_WHERE TEXT,
    D2_WHO TEXT,
    D3_ACTION TEXT,
    D3_DEPT TEXT,
    D3_DUEDATE TEXT,
    D3_FINISHDATE TEXT,
    D3_HDNCREATOR TEXT,
    D3_ITEM TEXT,
    D3_OWNER TEXT,
    D4_DESC TEXT,
    D4_NA TEXT,
    D4_ROOTCAUSE TEXT,
    D4_ROOTCAUSEESC TEXT,
    D4_ROOTTYPE TEXT,
    D4_TRAINER TEXT,
    D4_WHY1ESC TEXT,
    D4_WHY1OCC TEXT,
    D4_WHY2ESC TEXT,
    D4_WHY2OCC TEXT,
    D4_WHY3ESC TEXT,
    D4_WHY3OCC TEXT,
    D4_WHY4ESC TEXT,
    D4_WHY4OCC TEXT,
    D4_WHY5ESC TEXT,
    D4_WHY5OCC TEXT,
    D5_ACTION TEXT,
    D5_DEPT TEXT,
    D5_DUEDATE TEXT,
    D5_FINISHDATE TEXT,
    D5_HDNCREATOR TEXT,
    D5_ITEM TEXT,
    D5_OWNER TEXT
);
    """
]

for ddl in ddl_list:
    vn.train(ddl=ddl)

def train_with_csv(csv_path):
    sql_df = pd.read_csv(csv_path)
    for index, row in sql_df.iterrows():
        sql_command_1 = row['question']
        sql_command_2 = row['sql']
        try:
            vn.train(question=sql_command_1, sql=sql_command_2)
            print(f"SQL command executed successfully: {sql_command_1}")
        except Exception as e:
            print(f"Error executing SQL command: {sql_command_1}\nError: {e}")

train_with_csv("C:/Users/user/Downloads/LLM_Chat/後端程式/SQL_data/report.csv") #訓練資料路徑

df_information_schema = vn.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS where table_schema = 'test'")
plan = vn.get_training_plan_generic(df_information_schema)
vn.train(plan=plan)

def get_recommended_query_count(question):
    response = vn.generate_summary(f"根據問題 '{question}' 產生需要幾個不同的 SQL 查詢語句，範圍在 1 到 5 個之間")
    try:
        recommended_count = int(re.search(r'\d+', response).group())  # 提取數字
        return max(1, min(recommended_count, 5))  # 確保範圍在 1 到 5
    except (ValueError, AttributeError):
        return random.randint(1, 5) 

def generate_simplified_sql(base_sql, columns):
    # 根據提供的列名生成查詢語句
    column_string = ", ".join(columns)
    return base_sql.replace("SELECT *", f"SELECT {column_string}")

def get_relevant_columns(question):
    # 根據問題中的關鍵詞篩選相關欄位，還須新增
    if "根本原因" in question or "5why分析" in question:
        return ["D4_DESC", "D4_ROOTCAUSE", "D4_WHY1ESC", "D4_WHY2ESC", "D4_WHY3ESC", "D4_WHY4ESC", "D4_WHY5ESC"]
    elif "異常" in question or "問題描述" in question:
        return ["D2_WHAT", "D2_WHEN", "D2_WHO", "D2_WHERE", "D4_DESC", "D4_ROOTCAUSE"]
    elif "責任人" in question or "負責" in question:
        return ["D3_OWNER", "D5_OWNER", "D6_OWNER"]
    elif "有效性" in question or "成效" in question:
        return ["D6_VERIFICATION", "D6_ACTION"]
    elif "改進" in question or "矯正措施" in question:
        return ["D5_ACTION", "D5_OWNER", "D5_DEPT", "D5_DUEDATE", "D5_FINISHDATE"]
    # 默認欄位
    return ["D4_DESC", "D4_ROOTCAUSE", "D4_TRAINER"]

def generate_optimized_queries(base_sql, question):
    # 查詢條件列表
    query_conditions = [
        "LIMIT 10",                           # 限制返回記錄數
        "DISTINCT",                           # 查詢唯一值
        "ORDER BY D4_DESC",                   # 根據描述排序
        "COUNT(*) AS count",                  # 計算總數
        "HAVING COUNT(*) > 1",                # 篩選記錄數大於 1 的分組
        "WHERE D4_ROOTCAUSE IS NOT NULL",     # 篩選有根本原因的記錄
        "GROUP BY D3_OWNER",                  # 根據負責人分組
        "HAVING COUNT(*) > 1",                # 篩選記錄數大於 1 的分組
        "WHERE D5_ACTION IS NOT NULL",        # 篩選有建議的記錄
        "ORDER BY D3_FINISHDATE DESC"         # 根據完成日期降序排序
    ]

    # 生成 SQL 語法
    queries = []
    for i in range(min(len(query_conditions), 10)):
        if "DISTINCT" in query_conditions[i]:
            query = base_sql.replace("SELECT", "SELECT DISTINCT", 1)
        elif "COUNT(*)" in query_conditions[i]:
            query = base_sql.replace("SELECT *", f"SELECT {query_conditions[i]}")
        else:
            query = f"{base_sql} {query_conditions[i]}"

        queries.append(query)

    # 固定只返回 5 個最佳化語法
    return queries[:5]

# 定義 Flask API
app = Flask(__name__)
CORS(app)

@app.route('/Si/GetSQL', methods=['POST'])
def get_sql():
    data = request.json
    question = data.get('question')
    
    if not question:
        return jsonify({'error': '未提供問題'}), 400

    try:
        print(f"接收到的問題: {question}")

        # 通過 LLM 生成初始查詢語句
        prompt = apply_chat_template(sys_prompt, question)
        base_sql = vn.generate_sql(prompt)

        def clean_sql(sql):
            return re.sub(r'\s+', ' ', sql).strip()

        # 確保生成語句能匹配資料表結構
        schema = get_database_schema()
        table_name = extract_table_name(base_sql)  
        if not table_name:
            raise ValueError("無法從 SQL 中提取資料表名")

        if table_name in schema:
            all_columns = schema[table_name]
            if "OID" not in all_columns:
                raise ValueError("OID 欄位不存在於資料表中")
            column_list = ", ".join(all_columns)  # 動態生成欄位列表

            if "*" in base_sql:
                base_sql = base_sql.replace("*", column_list)  
            else:
                base_sql = base_sql.replace("SELECT", f"SELECT {column_list}", 1)

        # 添加篩選條件，確保查詢正確
        oid_condition = "OID IS NOT NULL"
        if "WHERE" in base_sql.upper():
            base_sql = re.sub(r"\bWHERE\b", f"WHERE {oid_condition} AND", base_sql, count=1, flags=re.IGNORECASE)
        else:
            base_sql += f" WHERE {oid_condition}"

        # 打印生成的基礎 SQL 語句
        print(f"生成的基礎 SQL: {base_sql}")

        # 使用生成查詢邏輯擴展語句到 5 個
        optimized_queries = generate_optimized_queries(base_sql, question)

        # 格式化輸出，確保語句的正確性
        output = {
            "question": question,
            "Result": {f"SQL{i+1}": clean_sql(query) for i, query in enumerate(optimized_queries[:5])}
        }

        # 儲存結果
        json_dir = 'getsql_results'
        os.makedirs(json_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        json_file_path = os.path.join(json_dir, f'getsql_result_{timestamp}.json')

        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)

        print(f'GetSQL結果已儲存在 {json_file_path}')
        return jsonify(output)

    except Exception as e:
        print(f"生成 SQL 時出錯: {e}")
        return jsonify({'error': f'生成 SQL 時出錯: {str(e)}'}), 500

def extract_table_name(sql):
    match = re.search(r"FROM\s+(\w+)", sql, re.IGNORECASE)
    return match.group(1) if match else None

@app.route('/Si/ParseSQL', methods=['POST'])
def parse_sql():
    data = request.json
    print("Received request data:", data) 
    sql_queries = {key: value for key, value in data.items() if key.startswith("SQL")}
    print("SQL Queries:", sql_queries)

    if not sql_queries:
        print("未解析到任何 SQL 語句")
        return jsonify({'error': '未提供 SQL 語句列表'}), 400

    try:
        results = {}
        descriptions = []

        for key, sql in sql_queries.items():
            sql = sql.replace("\n", " ")
            print(f"執行並解析 SQL 語句 {key}: {sql}")
            try:
                df_result = vn.run_sql(sql)
                if not df_result.empty:
                    result_json = df_result.to_json(orient='records')
                    results[key] = {
                        "sql": sql,
                        "result": json.loads(result_json)
                    }
                else:
                    results[key] = {
                        "sql": sql,
                        "result": []
                    }
                description = parse_sql_query(sql)
                descriptions.append(f"{key}: {description}")
            except Exception as e:
                results[key] = {
                    "sql": sql,
                    "result": f"執行出錯: {str(e)}"
                }

        # 僅當有多條 SQL 語句時生成文字總結
        if len(sql_queries) > 1:
            combined_description = "\n".join(descriptions)
            llm_summary_prompt = f"請總結以下 SQL 語句的主要意圖或作用：\n{combined_description}"
            empty_df = pd.DataFrame() 
            result_description = vn.generate_summary(llm_summary_prompt, df=empty_df)
            results["Result"] = result_description

        # 儲存 JSON 檔案
        json_dir = 'parsesql_results'
        os.makedirs(json_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        json_file_path = os.path.join(json_dir, f'parsesql_result_{timestamp}.json')

        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        
        print(f'ParseSQL結果已儲存在 {json_file_path}')
        return jsonify(results)

    except Exception as e:
        print(f"解析 SQL 語句時出錯: {e}")
        return jsonify({'error': f'解析 SQL 語句時出錯: {str(e)}'}), 500

def parse_sql_query(sql):
    """根據 SQL 語句的結構生成簡單的解釋。"""
    if "COUNT" in sql:
        return "計算記錄的總數"
    elif "DISTINCT" in sql:
        return "查詢唯一值"
    elif "ORDER BY" in sql:
        return "按指定欄位排序"
    elif "GROUP BY" in sql:
        return "按指定欄位分組"
    elif "LIMIT" in sql:
        return "限制返回的記錄數"
    elif "WHERE" in sql:
        return "篩選符合條件的記錄"
    else:
        return "基本查詢"

@app.route('/Si/SelectedRows', methods=['POST'])
def selected_rows_summary():
    try:
        data = request.json
        if not data:
            return jsonify({'error': '未提供任何資料'}), 400

        selected_rows = data.get('selectedRows', [])
        if not isinstance(selected_rows, list):
            return jsonify({'error': 'selectedRows 必須是一個列表'}), 400

        # 初始化摘要
        summary = [{"總計勾選資料筆數": len(selected_rows)}]

        for row in selected_rows:
            oid = row.get('OID', '未知')
            description = row.get('D4_DESC', '無描述')
            root_cause = row.get('D4_ROOTCAUSE', '無根本原因')

            # 生成精簡摘要
            concise_summary = generate_llm_prompt_for_summary(oid, description, root_cause)
            llm_summary = generate_summary_with_llm(concise_summary)

            summary.append({
                "OID": oid,
                "Summary": llm_summary
            })

        output = {
            "SelectedRowsSummary": summary
        }

        # 儲存 JSON 結果
        json_dir = 'selected_rows_results'
        os.makedirs(json_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        json_file_path = os.path.join(json_dir, f'selected_rows_{timestamp}.json')

        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)

        print(f'SelectedRows結果已儲存在 {json_file_path}')
        return jsonify(output)

    except Exception as e:
        print(f"處理勾選資料時出錯: {e}")
        return jsonify({'error': f'處理勾選資料時出錯: {str(e)}'}), 500

def generate_llm_prompt_for_summary(oid, description, root_cause):
    """
    根據 OID、描述和根本原因生成 LLM 摘要提示詞。
    """
    prompt = (
        f"OID: {oid}\n"
        f"描述: {description}\n"
        f"根本原因: {root_cause}\n\n"
        f"請生成簡短摘要，使用以下格式：\n"
        f"描述 - 根本原因 - 建議\n"
        f"要求:\n"
        f"1. 請使用繁體中文。\n"
        f"2. 總字數請限制在 150 字以內。\n"
    )
    return prompt

def generate_summary_with_llm(input_text):
    """
    使用 LLM 生成精簡摘要，限制字數。
    """
    try:
        if not input_text.strip():
            return "輸入內容為空，無法生成摘要。"

        # 使用空的 DataFrame 作為參數
        empty_df = pd.DataFrame()

        # 使用 LLM 模型生成摘要
        response = vn.generate_summary(input_text, df=empty_df)

        # 限制輸出字數在 150 字以內
        trimmed_response = response.strip()
        if len(trimmed_response) > 150:
            trimmed_response = trimmed_response[:147] + "..."  # 添加省略號

        return trimmed_response

    except Exception as e:
        error_message = f"生成摘要時出錯: {e}"
        print(error_message)
        return "生成摘要失敗，請稍後重試。"

if __name__ == '__main__':  
    app.run(host='0.0.0.0', port=8088) 