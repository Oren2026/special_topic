# 編譯器說明與程式流程

本文件說明 `compiler.c` 中 while 語法的修正，以及整體執行流程。

---

## 1. while 語法修正

原先的程式碼中，`while` 無法正常執行：

- 在 `compiler.c` 裡面沒有定義 `TK_WHILE`，因此當遇到 `while` 字串時，
  會被當成 `TK_ID`（一般變數）處理。
- 必須新增 `while` 的判斷與中間碼生成邏輯。

### 變更項目

1. 在 [2.詞法解析] 的 `typedef enum()` 中加入 `TK_WHILE`。
2. 在 `next_token` 函式內的
   `else if(isalpha(*src) || *src == '_')` 分支中，增加對 `while` 的辨識
   並處理相應行為。
3. 在 `statement` 函式中：
   - 增加 `while` 相關讀取動作。
   - 增加必要的變數。
   - 使用 `JMP`、`JMP_F` 指令來輸出適當的中間碼。

上述改動讓 `while` 迴圈的編碼與執行正常運作。

---

## 2. 程式執行流程

可以從 `int main()` 觀察整體運作：

1. **檔案存在檢查**
   - 首先確認輸入的執行檔案是否存在，並提供錯誤回報。  
2. **讀取內容**
   - 把檔案讀取到 `buffer`，然後將 `buffer` 的內容複製到 `src`。
3. **初始化語法分析**
   - 呼叫 `next_token()` 取得第一個 token，作為後續解析的起點。
4. **編譯程序**
   - `parse_program()` 根據 `cur_token` 做不同的判斷。
   - 呼叫 `statement()` 處理 token（包含 `type` 與 `text`），
     並透過 `emit()` 將結果儲存到 `quads[]` 中，同時印出中間碼。
5. **虛擬機執行**
   - 執行 `vm()` 函式：
     - 將 `quads` 縮寫成 `q` 並判斷要執行的操作 (`q.op`)。
     - 使用 `param_stack[]`（中轉站）與 `stack[]` 完成運算，
       最終結果放回 `stack[]`。
6. **輸出結果**
   - 當 while 迴圈結束時，將 `stack[]` 中的值逐一印出。
7. **釋放記憶體**
   - 使用 `free(buffer)` 釋放先前分配的空間。
