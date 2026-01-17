// ==UserScript==
// @name         LegalDoc 判例クロールツール（ダウンロード制御強化版）
// @namespace    http://tampermonkey.net/
// @version      1.2
// @description  自動ダウンロードチェックボックスと手動ダウンロードボタンを追加し、カスタム総量に対応
// @author       Gemini
// @match        https://legaldoc.jp/hanrei/hanrei-search?cid=1*
// @grant        none
// @require      https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js
// ==/UserScript==

(function() {
    'use strict';

    // --- get total ---
    function getPageTotal() {
        const totalElem = document.querySelector('.result-message.success');
        if (totalElem) {
            // 使用正则匹配数字，例如从 "条件に一致する判例：67110件" 中提取 67110
            const match = totalElem.innerText.match(/\d+/);
            return match ? parseInt(match[0]) : 67110;
        }
        return 0; // 找不到标签时的默认回退值
    }

    console.log(`get total: ${getPageTotal()}`);

    const CONFIG = {
        step: 20,
        defaultTotal: getPageTotal(),
        targetUrl: "https://legaldoc.jp/hanrei/hanrei-search?cid=1",
        maxRetries: 3,
        delay: 1000,
        retryDelay: 3000
    };

    let results = [];
    let failedStarts = [];
    let isRunning = false;
    let dynamicTotal = CONFIG.defaultTotal;

    // --- UIパネルを作成 ---
    const panel = document.createElement('div');
    panel.innerHTML = `
        <div id="crawl-panel" style="position:fixed; top:10px; right:10px; z-index:9999; background:white; border:2px solid #333; padding:15px; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.2); width:260px; font-family:sans-serif;">
            <h4 style="margin:0 0 10px 0; color:#333;">判例クロールコンソール</h4>
            
            <div style="font-size:12px; margin-bottom:12px; background:#f8f9fa; padding:8px; border-radius:4px;">
                進捗: <span id="p-current" style="font-weight:bold;">0</span> / <span id="p-total">${CONFIG.defaultTotal}</span><br>
                成功: <span id="p-success" style="color:green; font-weight:bold;">0</span> | 
                失敗: <span id="p-fail" style="color:red; font-weight:bold;">0</span>
            </div>

            <div style="margin-bottom:12px;">
                <label style="font-size:12px; cursor:pointer; display:flex; align-items:center;">
                    <input type="checkbox" id="auto-download-cb" checked style="margin-right:8px;"> 完了後自動ダウンロード
                </label>
            </div>

            <button id="start-btn" style="width:100%; padding:8px; background:#28a745; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold; margin-bottom:8px;">クロール開始</button>
            <button id="download-btn" style="width:100%; padding:8px; background:#007bff; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">XML結果をダウンロード</button>
            
            <div id="p-status" style="margin-top:10px; font-size:11px; color:#666; height:40px; overflow-y:auto; border-top:1px solid #eee; padding-top:5px; line-height:1.4;">開始待機中...</div>
        </div>
    `;
    document.body.appendChild(panel);

    // --- 核心ロジック ---

    async function fetchPage(start, viewState) {
        const bodyData = new URLSearchParams({
            "jakarta.faces.partial.ajax": "true",
            "jakarta.faces.source": "j_idt209-courtsDataTable",
            "jakarta.faces.partial.execute": "j_idt209-courtsDataTable",
            "jakarta.faces.partial.render": "j_idt209-courtsDataTable",
            "jakarta.faces.behavior.event": "page",
            "jakarta.faces.partial.event": "page",
            "j_idt209-courtsDataTable_pagination": "true",
            "j_idt209-courtsDataTable_first": start,
            "j_idt209-courtsDataTable_rows": CONFIG.step,
            "j_idt209": "j_idt209",
            "jakarta.faces.ViewState": viewState
        });

        const response = await axios.post(CONFIG.targetUrl, bodyData.toString(), {
            headers: { 
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8", 
                "faces-request": "partial/ajax" 
            },
            timeout: 15000 
        });

        return response.data;
    }

    async function startCrawl() {
        if(isRunning) return;

        const userInput = prompt("クロールするデータの総数を入力してください (totalData):", dynamicTotal);
        if (userInput === null) return;
        
        const parsedInput = parseInt(userInput);
        if (isNaN(parsedInput) || parsedInput <= 0) {
            alert("有効な数字を入力してください！");
            return;
        }
        
        dynamicTotal = parsedInput;
        document.getElementById('p-total').innerText = dynamicTotal;
        
        // ステータスをリセット
        results = [];
        failedStarts = [];
        isRunning = true;
        document.getElementById('start-btn').disabled = true;
        document.getElementById('start-btn').style.opacity = "0.6";
        document.getElementById('start-btn').innerText = "クロール中...";

        let currentViewState = document.getElementById("j_id1-jakarta.faces.ViewState-0")?.value;
        
        if (!currentViewState) {
            updateStatus("❌ エラー: ViewStateトークンを取得できませんでした");
            resetUI();
            return;
        }

        // 1. メインループ
        for (let start = 0; start < dynamicTotal; start += CONFIG.step) {
            try {
                updateStatus(`📡 クロール中: ${start}`);
                const xml = await fetchPage(start, currentViewState);
                
                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(xml, "text/xml");
                const vsNode = xmlDoc.querySelector('update[id*="jakarta.faces.ViewState"]');
                if (vsNode) currentViewState = vsNode.textContent;

                results.push({ start, xml });
                updateCounter('p-success', results.length);
                updateCounter('p-current', Math.min(start + CONFIG.step, dynamicTotal));
                
                await new Promise(r => setTimeout(r, CONFIG.delay));
            } catch (e) {
                failedStarts.push({ start, retryCount: 0 });
                updateCounter('p-fail', failedStarts.length);
                updateStatus(`⚠️ 失敗: ${start}`);
            }
        }

        // 2. 欠落補完リトライ
        if (failedStarts.length > 0) {
            updateStatus(`🔄 失敗した ${failedStarts.length} 件をリトライ中...`);
            while (failedStarts.length > 0) {
                const task = failedStarts.shift();
                if (task.retryCount >= CONFIG.maxRetries) continue;

                try {
                    updateStatus(`♻️ リトライ: ${task.start} (${task.retryCount + 1})`);
                    const xml = await fetchPage(task.start, currentViewState);
                    results.push({ start: task.start, xml });
                    
                    updateCounter('p-success', results.length);
                    updateCounter('p-fail', failedStarts.length);
                    await new Promise(r => setTimeout(r, CONFIG.retryDelay));
                } catch (e) {
                    task.retryCount++;
                    failedStarts.push(task);
                    await new Promise(r => setTimeout(r, CONFIG.retryDelay));
                }
            }
        }

        updateStatus("✅ クロールタスク終了");
        
        // 3. 自動ダウンロード判定
        if (document.getElementById('auto-download-cb').checked) {
            exportXml();
        }
        resetUI();
    }

    function exportXml() {
        if (results.length === 0) {
            alert("現在クロールされたデータはありません！");
            return;
        }

        updateStatus("💾 XMLファイル構築中...");
        
        // クローンして並べ替え、元の結果配列には影響を与えない
        const sortedResults = [...results].sort((a, b) => a.start - b.start);

        let finalXml = `<?xml version="1.0" encoding="UTF-8"?>\n<root>\n`;
        sortedResults.forEach(item => {
            const cleanXml = item.xml.replace(/<\?xml.*?\?>/i, "").trim();
            finalXml += `  <entry start="${item.start}" step="${CONFIG.step}">\n`;
            finalXml += `    <partial-response>${cleanXml}</partial-response>\n`;
            finalXml += `  </entry>\n`;
        });
        finalXml += `</root>`;

        const blob = new Blob([finalXml], { type: 'text/xml' });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `legal_export_n${results.length}_${Date.now()}.xml`;
        link.click();
        
        updateStatus("💾 ファイルがエクスポートされました");
    }

    // --- ユーティリティ関数 ---
    function updateStatus(msg) {
        document.getElementById('p-status').innerText = msg;
    }

    function updateCounter(id, val) {
        document.getElementById(id).innerText = val;
    }

    function resetUI() {
        const btn = document.getElementById('start-btn');
        btn.disabled = false;
        btn.style.opacity = "1";
        btn.innerText = "クロール開始";
        isRunning = false;
    }

    // イベントをバインド
    document.getElementById('start-btn').addEventListener('click', startCrawl);
    document.getElementById('download-btn').addEventListener('click', exportXml);

})();