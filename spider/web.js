async function startCrawl() {
    const step = 20;
    const totalData = 67110;
    const targetUrl = "https://legaldoc.jp/hanrei/hanrei-search?cid=1";
    const maxRetries = 3; // 各失敗項目の最大リトライ回数
    
    const results = [];
    let failedStarts = [];

    // 初期ViewState
    let currentViewState = document.getElementById("j_id1-jakarta.faces.ViewState-0").value;

    /**
     * コアリクエスト関数：単一リクエストロジックをカプセル化
     */
    async function fetchPage(start) {
        const bodyData = new URLSearchParams({
            "jakarta.faces.partial.ajax": "true",
            "jakarta.faces.source": "j_idt209-courtsDataTable",
            "jakarta.faces.partial.execute": "j_idt209-courtsDataTable",
            "jakarta.faces.partial.render": "j_idt209-courtsDataTable",
            "jakarta.faces.behavior.event": "page",
            "jakarta.faces.partial.event": "page",
            "j_idt209-courtsDataTable_pagination": "true",
            "j_idt209-courtsDataTable_first": start,
            "j_idt209-courtsDataTable_rows": step,
            "j_idt209": "j_idt209",
            "jakarta.faces.ViewState": currentViewState
        });

        const response = await axios.post(targetUrl, bodyData.toString(), {
            headers: { 
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8", 
                "faces-request": "partial/ajax" 
            },
            timeout: 15000 
        });

        const xmlText = response.data;
        
        // ViewStateを更新
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(xmlText, "text/xml");
        const vsNode = xmlDoc.querySelector('update[id*="jakarta.faces.ViewState"]');
        if (vsNode) {
            currentViewState = vsNode.textContent;
        }

        return xmlText;
    }

    // --- 第1ラウンド：メインクロールループ ---
    console.log("🚀 第一ラウンドのメインクロール開始...");
    for (let start = 0; start < totalData; start += step) {
        try {
            console.log(`📡 リクエスト中: ${start}`);
            const xml = await fetchPage(start);
            results.push({ start, step, xml });
            await new Promise(r => setTimeout(r, 1000));
        } catch (e) {
            console.error(`❌ 初回失敗 (start: ${start}):`, e.message);
            failedStarts.push({ start, retryCount: 0 });
        }
    }

    // --- 第2ラウンド：欠損補完とリトライループ ---
    if (failedStarts.length > 0) {
        console.log(`🔄 ${failedStarts.length} 個の失敗タスクが見つかりました。リトライを開始します...`);
        
        while (failedStarts.length > 0) {
            const task = failedStarts.shift(); // 最初の失敗タスクを取り出す
            
            if (task.retryCount >= maxRetries) {
                console.error(`🚫 最大リトライ回数に達しました。start: ${task.start} を諦めます`);
                continue; 
            }

            try {
                console.log(`♻️ リトライ中 (${task.retryCount + 1}/${maxRetries}): ${task.start}`);
                const xml = await fetchPage(task.start);
                results.push({ start: task.start, step, xml });
                await new Promise(r => setTimeout(r, 2000)); // リトライ時のインターバルは少し長め
            } catch (e) {
                console.error(`❌ リトライでも失敗 (start: ${task.start}):`, e.message);
                task.retryCount++;
                failedStarts.push(task); // 再度キューの末尾に戻す
                await new Promise(r => setTimeout(r, 5000)); // 失敗後の休憩時間は長め
            }
        }
    }

    // --- 3. XMLの構築と保存 ---
    console.log("✅ 全てのクロール/リトライ試行終了。start順にソートしてエクスポートしています...");
    
    // startの昇順で並び替え、生成されるXMLの順序が正常になるようにする
    results.sort((a, b) => a.start - b.start);

    let finalXml = `<?xml version="1.0" encoding="UTF-8"?>\n<root>\n`;
    results.forEach(item => {
        const cleanXml = item.xml.replace(/<\?xml.*?\?>/i, "").trim();
        finalXml += `  <entry start="${item.start}" step="${item.step}">\n`;
        finalXml += `    <partial-response>${cleanXml}</partial-response>\n`;
        finalXml += `  </entry>\n`;
    });
    finalXml += `</root>`;

    saveToFile(finalXml, `legal_crawl_${Date.now()}.xml`);
}

function saveToFile(content, fileName) {
    const blob = new Blob([content], { type: 'text/xml' });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = fileName;
    link.click();
    URL.revokeObjectURL(link.href);
    console.log(`💾 ファイルのエクスポート完了: ${fileName}`);
}

// 実行
// startCrawl();