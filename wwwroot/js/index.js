const replies = [
    { text: 'SQL1', details: "" },
    { text: 'SQL2', details: "" },
    { text: 'SQL3', details: "" },
    { text: 'SQL4', details: "" },
    { text: 'SQL5', details: "" }
];

// 用於存儲所有查詢的歷史紀錄
const queryHistory = [];

// 用於存儲勾選的資料
const selectedData = {};

$(document).ready(function () {

    $('#send-btn').click(function () {

        var message = $('#user-input').val();
        if (message.trim() === '') return;

        // 清空選擇的資料
        for (let key in selectedData) {
            if (selectedData.hasOwnProperty(key)) {
                selectedData[key] = [];
            }
        }
        console.log("已清空選擇的資料:", selectedData);

        // Append user message to chat box
        $('#chat-box').append('<div class="chat-message user-message">' + message + '</div>');

        // Get API 詢問LLM 取得SQL
        fetch('http://localhost:8088/Si/GetSQL', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: message
            })
        })
            .then(response => response.json())
            .then(data => {
                console.log("SQL查詢已取得：", data);

                // 將 SQL 結果存儲到 replies 陣列
                replies.find(reply => reply.text == "SQL1").details = data['Result']['SQL1'];
                replies.find(reply => reply.text == "SQL2").details = data['Result']['SQL2'];
                replies.find(reply => reply.text == "SQL3").details = data['Result']['SQL3'];
                replies.find(reply => reply.text == "SQL4").details = data['Result']['SQL4'];
                replies.find(reply => reply.text == "SQL5").details = data['Result']['SQL5'];

                // 保存查詢結果到歷史紀錄
                queryHistory.push(JSON.parse(JSON.stringify(replies)));
                console.log("查詢歷史紀錄：", queryHistory);

                // 動態顯示每個 SQL 按鈕
                let chatBoxContent = '<div class="test-response">';
                chatBoxContent += '<div class="test-message" onclick="showModal(\'SQL1\', ' + (queryHistory.length - 1) + ')">SQL1</div>';
                chatBoxContent += '<div class="test-message" onclick="showModal(\'SQL2\', ' + (queryHistory.length - 1) + ')">SQL2</div>';
                chatBoxContent += '<div class="test-message" onclick="showModal(\'SQL3\', ' + (queryHistory.length - 1) + ')">SQL3</div>';
                chatBoxContent += '<div class="test-message" onclick="showModal(\'SQL4\', ' + (queryHistory.length - 1) + ')">SQL4</div>';
                chatBoxContent += '<div class="test-message" onclick="showModal(\'SQL5\', ' + (queryHistory.length - 1) + ')">SQL5</div>';
                chatBoxContent += '</div>';
                chatBoxContent += '<button class="parse-button" onclick="parseData()">點擊進行被勾選資料解析</button>';

                // Append buttons to chat box
                $('#chat-box').append(chatBoxContent);
            })
            .catch(error => {
                $('#chat-box').append('<div class="chat-message bot-message">Error :[' + error + '], please try again.</div>');
                console.error('Error:', error);
            });
    });

});

function parseData() {
    // 顯示解析資料的訊息
    $('#chat-box').append('<div class="chat-message user-message">' + "開始解析資料" + '</div>');

    // 發送已勾選資料到後端
    sendSelectedRowsToServer();
}

function sendSelectedRowsToServer() {
    const selectedRowsPayload = {
        selectedRows: Object.values(selectedData).flat()
    };

    fetch('http://localhost:8088/Si/SelectedRows', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(selectedRowsPayload)
    })
    .then(response => response.json())
    .then(data => {
        console.log("勾選資料解析結果：", data);

        let chatBoxContent = '<div class="chat-message bot-message"><b>解析結果:</b><br>';

        // 總計筆數
        chatBoxContent += `<div>總計勾選資料筆數: ${data.SelectedRowsSummary[0]["總計勾選資料筆數"]}</div><br>`;

        // 每筆資料摘要
        for (let i = 1; i < data.SelectedRowsSummary.length; i++) {
            const summary = data.SelectedRowsSummary[i];
            chatBoxContent += `
                <div>
                    <b>OID:</b> ${summary.OID}<br>
                    <b>摘要:</b><br>
                    <pre>${summary.Summary}</pre>
                </div><br>
            `;
        }

        chatBoxContent += '</div>';
        $('#chat-box').append(chatBoxContent);
    })
    .catch(error => {
        console.error('勾選資料解析失敗:', error);
        $('#chat-box').append('<div class="chat-message bot-message">勾選資料解析失敗，請稍後再試。</div>');
    });
}


// 定義 showModal 函數
function showModal(text, queryIndex) {
    const details = queryHistory[queryIndex].find(reply => reply.text == text).details;

    const modalTitle = document.getElementById('modal-title');
    const modalDescription = document.getElementById('modal-description');
    const modal = document.getElementById('modal');

    if (modalTitle && modalDescription && modal) {
        modalTitle.textContent = text;
        modalDescription.textContent = details;
        modal.style.display = 'flex';
    } else {
        console.error('某些元素未正確選取到');
    }

    fetch('http://localhost:8088/Si/ParseSQL', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            SQL: details
        })
    })
        .then(response => response.json())
        .then(data => {
            console.log(data);

            let tableContainer = document.getElementById("tableContainer");
            let table = createTable(data['SQL'], text);
            tableContainer.innerHTML = ''; // 清空容器內容
            tableContainer.appendChild(table);
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

// 增加“重新解析”按鈕
function reparseQuery(queryIndex) {
    const query = queryHistory[queryIndex];
    const message = query.map(reply => reply.details).join(', '); // 這只是示例，具體根據你的 SQL 內容
    $('#chat-box').append('<div class="chat-message user-message">' + "重新解析查詢" + '</div>');
    
    fetch('http://localhost:8088/Si/ParseSQL', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            SQL: message // 使用之前的查詢進行解析
        })
    })
        .then(response => response.json())
        .then(data => {
            // 顯示結果
            const summaryContent = data.SQLSummary.join('<br>'); 
            const chatBoxContent = '<div class="chat-message bot-message">' + summaryContent + '</div>';
            $('#chat-box').append(chatBoxContent);
        })
        .catch(error => {
            console.error('重新解析失敗:', error);
            $('#chat-box').append('<div class="chat-message bot-message">重新解析失敗，請稍後再試。</div>');
        });
}


function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

// 創建表格，並為每行資料添加勾選框功能
function createTable(data, sqlKey) {
    if (!data || !data.result || !Array.isArray(data.result) || data.result.length === 0) {
        console.error("Data is empty or not defined");
        return document.createTextNode("No data available");
    }

    if (!selectedData[sqlKey]) {
        selectedData[sqlKey] = [];
    }

    let table = document.createElement("table");

    // 表頭
    let thead = document.createElement("thead");
    let headerRow = document.createElement("tr");

    // 添加勾選框列
    let selectHeader = document.createElement("th");
    selectHeader.textContent = "選擇";
    headerRow.appendChild(selectHeader);

    // 使用 OID 作為表頭的第一個欄位
    let titleHeader = document.createElement("th");
    titleHeader.textContent = "OID (Title)";
    headerRow.appendChild(titleHeader);

    // 獲取其他欄位作為表頭
    let headers = Object.keys(data.result[0]).filter(key => key !== 'OID');
    headers.forEach(header => {
        let th = document.createElement("th");
        th.textContent = header;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // 表體
    let tbody = document.createElement("tbody");
    data.result.forEach((row, index) => {
        let tr = document.createElement("tr");

        // 添加勾選框
        let selectCell = document.createElement("td");
        let checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = selectedData[sqlKey].some(selected => JSON.stringify(selected) === JSON.stringify(row));
        checkbox.addEventListener("change", (event) => handleRowSelection(event, row, sqlKey));
        selectCell.appendChild(checkbox);
        tr.appendChild(selectCell);

        // 在 createTable 函數中，將 OID 欄位改為超連結
        let titleCell = document.createElement("td");
        let link = document.createElement("a");
        link.href = "#"; // 避免刷新頁面
        link.textContent = row['OID'] || ''; // OID 顯示
        link.addEventListener("click", () => openDetailsPage(row)); // 點擊事件
        titleCell.appendChild(link);
        tr.appendChild(titleCell);

        // 添加其他欄位
        headers.forEach(header => {
            let td = document.createElement("td");
            td.textContent = row[header] !== null ? row[header] : ''; // 處理 null 值
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });

    table.appendChild(tbody);

    return table;
}

// 處理行勾選事件
function handleRowSelection(event, row, sqlKey) {
    if (!selectedData[sqlKey]) {
        selectedData[sqlKey] = [];
    }

    if (event.target.checked) {
        // 如果被勾選，添加到 selectedData
        selectedData[sqlKey].push(row);
    } else {
        // 如果取消勾選，從 selectedData 移除
        selectedData[sqlKey] = selectedData[sqlKey].filter(selected => JSON.stringify(selected) !== JSON.stringify(row));
    }

    console.log("目前已選擇的資料：", selectedData);
}

for (let key in selectedData) {
    if (selectedData.hasOwnProperty(key)) {
        selectedData[key] = [];
    }
}

function createVerticalTable(row) {
    let table = document.createElement("table");
    table.style.borderCollapse = "collapse";
    table.style.width = "100%";

    Object.keys(row).forEach(key => {
        let tr = document.createElement("tr");

        // 表頭 (欄位名稱)
        let th = document.createElement("th");
        th.textContent = key;
        th.style.border = "1px solid #ccc";
        th.style.backgroundColor = "#f4f4f4";
        th.style.padding = "8px";
        th.style.textAlign = "left";
        th.style.width = "30%";
        tr.appendChild(th);

        // 表身 (數據)
        let td = document.createElement("td");
        td.textContent = row[key] !== null && row[key] !== undefined ? row[key] : "N/A";
        td.style.border = "1px solid #ccc";
        td.style.padding = "8px";
        td.style.textAlign = "left";
        tr.appendChild(td);

        table.appendChild(tr);
    });

    return table;
}

function openDetailsPage(row) {
    let newPage = window.open("", "_blank");
    newPage.document.write("<html><head><title>詳細資料</title><style>");
    newPage.document.write(
        "body { font-family: Arial, sans-serif; margin: 20px; }" +
        "table { border-collapse: collapse; width: 100%; margin-top: 20px; }" +
        "th, td { border: 1px solid #ccc; padding: 10px; text-align: left; }" +
        "th { background-color: #f4f4f4; width: 30%; }"
    );
    newPage.document.write("</style></head><body>");
    newPage.document.write('<h1>詳細資料：OID ' + row['OID'] + '</h1>');

    // 生成直列表格
    let table = createVerticalTable(row);
    newPage.document.body.appendChild(table);

    newPage.document.write("</body></html>");
    newPage.document.close();
}
