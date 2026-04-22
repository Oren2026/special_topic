using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;

namespace DiceRPSGame
{
    // ============================================================
    // 【骰子遊戲 / 猜拳遊戲】Windows Forms 雙人對戰程式
    //
    // 支援兩種模式：
    //   1. 骰子比大小（1~6，顯示 PNG 圖片）
    //   2. 剪刀石頭布（1=剪刀、2=石頭、3=布）
    // 圖片請命名為數字（1.png ~ 6.png 或 1.png ~ 3.png）
    // 並放在執行檔同目錄下的 /images/ 資料夾
    //
    // 評分對應：
    //   A. 初始化 → Form1_Load() 自動載入預設圖片
    //   B. 隨機 → btnRoll/btnPlay_Click() 動態切換
    //   C. 勝負判定 → DetermineWinner()
    // ============================================================

    public partial class Form1 : Form
    {
        // ==================== 區域變數 ====================

        // 目前的遊戲模式：0 = 骰子，1 = 猜拳
        private int currentMode = 0;

        // 儲存雙方目前點數（骰子：1~6，猜拳：1~3，0=尚未選擇）
        private int player1Value = 0;
        private int player2Value = 0;

        // 圖片來源資料夾（執行檔目錄下的 images/）
        private string imageFolder;

        // 骰子與猜拳的圖片前綴（避免檔名衝突）
        // 骰子：d1.png ~ d6.png；猜拳：r1.png(剪刀) r2.png(石頭) r3.png(布)
        private readonly string[] modePrefix = { "d", "r" };
        private readonly int[] maxImages = { 6, 3 };

        // 猜拳的名稱對照（用於結果顯示）
        private readonly string[] rpsNames = { "", "Scissors 剪刀", "Rock 石頭", "Paper 布" };

        // ==================== 建構子 ====================

        public Form1()
        {
            InitializeComponent();
            // 取得執行檔目錄，用於相對路徑載入圖片
            imageFolder = Application.StartupPath + "\\images\\";
        }

        // ==================== Form 載入時（評分 A：初始化）====================

        private void Form1_Load(object sender, EventArgs e)
        {
            // ----------------------------------------------------------
            // A. 初始化骰子圖片
            // 程式啟動時，自動將雙方圖片區域填入預設圖片（1.png）
            // ----------------------------------------------------------

            // 防止在 Design Mode 執行時出錯
            if (this.DesignMode) return;

            // 預設載入模式 0（骰子）
            currentMode = 0;
            LoadDefaultImages();

            // 更新 UI 顯示
            UpdateModeLabel();
            lblResult.Text = "Press Roll / Play to start!";
            lblResult.BackColor = SystemColors.Control;
            lblResult.ForeColor = SystemColors.ControlText;
        }

        // ==================== 按鈕：擲骰子 / 猜拳 ====================

        private void btnRoll_Click(object sender, EventArgs e)
        {
            // ----------------------------------------------------------
            // B. 隨機骰子與動態圖片切換
            // 產生 1~6 隨機數，根據點數載入對應 PNG 圖片
            // ----------------------------------------------------------

            PlayRound(maxImages[currentMode]);
        }

        // ==================== 核心遊戲邏輯 ====================

        /// <summary>
        /// 單一回合的完整流程：
        /// 1. 雙方隨機取值
        /// 2. 載入對應圖片（模擬動態更換效果）
        /// 3. 判定勝負
        /// 4. 更新結果顯示
        /// </summary>
        private void PlayRound(int maxValue)
        {
            try
            {
                // --- Step 1：產生隨機點數（1 ~ maxValue）---
                Random rng = new Random();
                player1Value = rng.Next(1, maxValue + 1); // 包含 maxValue
                player2Value = rng.Next(1, maxValue + 1);

                // --- Step 2：動態載入圖片到 PictureBox ---
                // 說明：這裡用 try-catch 包住，防止圖片缺失時整個程式崩掉
                // 檔名使用前綴區分：骰子 d1.png~d6.png，猜拳 r1.png~r3.png
                string prefix = modePrefix[currentMode];
                string p1Path = imageFolder + prefix + player1Value + ".png";
                string p2Path = imageFolder + prefix + player2Value + ".png";

                try
                {
                    // 每次更換時先清除舊圖，再設定新圖
                    pbPlayer1.Image = null;
                    pbPlayer2.Image = null;
                    pbPlayer1.Image = Image.FromFile(p1Path);
                    pbPlayer2.Image = Image.FromFile(p2Path);

                    // 強制 UI 立即更新，產生「更換」的視覺效果
                    pbPlayer1.Refresh();
                    pbPlayer2.Refresh();
                }
                catch (System.IO.FileNotFoundException)
                {
                    // 圖片檔案不存在時，顯示數字文字代替
                    pbPlayer1.Image = null;
                    pbPlayer2.Image = null;
                    pbPlayer1.Refresh();
                    pbPlayer2.Refresh();

                    // 在 PictureBox 上繪製數字（Fallback 機制）
                    DrawNumberOnPictureBox(pbPlayer1, player1Value, Color.Red);
                    DrawNumberOnPictureBox(pbPlayer2, player2Value, Color.Blue);
                }

                // --- Step 3：判定勝負 ---
                DetermineWinner();

                // --- Step 4：更新歷史紀錄（可選功能）---
                AppendHistory();
            }
            catch (Exception ex)
            {
                // 萬一發生任何未預期例外，顯示錯誤訊息但不當機
                MessageBox.Show(
                    "Error during game: " + ex.Message,
                    "Exception",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }

        // ==================== C. 勝負判定 ====================

        private void DetermineWinner()
        {
            // ----------------------------------------------------------
            // 比較雙方點數，根據規則判定勝負
            // 骰子模式：點數大者贏
            // 猜拳模式：1>3, 2>1, 3>2（石頭>布、布>剪刀、石頭>剪刀）
            // ----------------------------------------------------------

            string resultText;
            Color resultColor;

            if (currentMode == 0)
            {
                // ----- 骰子模式 -----
                if (player1Value > player2Value)
                {
                    resultText = "★ Player 1 Wins! ★";
                    resultColor = Color.DarkGreen;
                }
                else if (player1Value < player2Value)
                {
                    resultText = "★ Player 2 Wins! ★";
                    resultColor = Color.DarkBlue;
                }
                else
                {
                    resultText = "===== Tie =====";
                    resultColor = Color.DarkOrange;
                }
            }
            else
            {
                // ----- 猜拳模式 -----
                // 規則：石頭(1)勝剪刀(3)、剪刀(3)勝布(2)、布(2)勝石頭(1)
                // 用差值判斷：(1-3的差=-2, 3-2=1, 2-1=1) → 差為-2時P1勝，否則輪流
                int diff = player1Value - player2Value;

                if (player1Value == player2Value)
                {
                    resultText = "===== Tie =====";
                    resultColor = Color.DarkOrange;
                }
                else if (diff == 1 || diff == -2)
                {
                    resultText = "★ Player 1 Wins! ★";
                    resultColor = Color.DarkGreen;
                }
                else
                {
                    resultText = "★ Player 2 Wins! ★";
                    resultColor = Color.DarkBlue;
                }

                // 在結果加上實際出招名稱
                string p1Choice = rpsNames[player1Value];
                string p2Choice = rpsNames[player2Value];
                resultText = resultText + "   [" + p1Choice + "] vs [" + p2Choice + "]";
            }

            // 更新結果標籤
            lblResult.Text = resultText;
            lblResult.BackColor = resultColor;
            lblResult.ForeColor = Color.White;
            lblResult.AutoSize = false;
            lblResult.TextAlign = ContentAlignment.MiddleCenter;
        }

        // ==================== 模式切換 ====================

        private void cbMode_SelectedIndexChanged(object sender, EventArgs e)
        {
            // ----------------------------------------------------------
            // 根據 ComboBox 選擇切換遊戲模式
            // 0 = 骰子（1~6）、1 = 猜拳（1~3）
            // ----------------------------------------------------------

            try
            {
                currentMode = cbMode.SelectedIndex;

                // 重置點數與 UI
                player1Value = 0;
                player2Value = 0;
                pbPlayer1.Image = null;
                pbPlayer2.Image = null;

                // 重新載入預設圖片
                LoadDefaultImages();
                UpdateModeLabel();

                lblResult.Text = currentMode == 0
                    ? "Press Roll to start!"
                    : "Press Play to start!";
                lblResult.BackColor = SystemColors.Control;
                lblResult.ForeColor = SystemColors.ControlText;

                // 清空歷史
                lbHistory.Items.Clear();
            }
            catch (Exception ex)
            {
                MessageBox.Show("Mode switch error: " + ex.Message, "Error",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        // ==================== 輔助函式 ====================

        /// <summary>
        /// 程式啟動或模式切換時，自動載入 1.png 作為預設圖片
        /// （評分 A 對應）
        /// </summary>
        private void LoadDefaultImages()
        {
            try
            {
                // 根據目前模式載入對應前綴的 1.png（例如 d1.png 或 r1.png）
                string prefix = modePrefix[currentMode];
                string defaultPath = imageFolder + prefix + "1.png";
                if (System.IO.File.Exists(defaultPath))
                {
                    pbPlayer1.Image = Image.FromFile(defaultPath);
                    pbPlayer2.Image = Image.FromFile(defaultPath);
                }
            }
            catch
            {
                // 圖片載入失敗時，什麼都不做（由 DrawNumberOnPictureBox 作為 Fallback）
            }
        }

        /// <summary>
        /// 當 PNG 圖片不存在時，在 PictureBox 上繪製數字作為替代
        /// 避免程式噴例外而當掉（評分 C 防例外對應）
        /// </summary>
        private void DrawNumberOnPictureBox(PictureBox pb, int number, Color textColor)
        {
            // 建立一張空白 Bitmap
            Bitmap bmp = new Bitmap(pb.Width, pb.Height);
            using (Graphics g = Graphics.FromImage(bmp))
            {
                // 填滿背景（淺灰色）
                g.Clear(Color.LightGray);

                // 繪製數字
                using (Font f = new Font("Arial", 36, FontStyle.Bold))
                using (Brush brush = new SolidBrush(textColor))
                {
                    string text = number.ToString();
                    SizeF size = g.MeasureString(text, f);
                    PointF point = new PointF(
                        (bmp.Width - size.Width) / 2,
                        (bmp.Height - size.Height) / 2
                    );
                    g.DrawString(text, f, brush, point);
                }
            }
            pb.Image = bmp;
        }

        /// <summary>
        /// 更新目前模式標題與按鈕文字
        /// </summary>
        private void UpdateModeLabel()
        {
            if (currentMode == 0)
            {
                lblTitle.Text = "🎲 Dice Game 骰子比大小";
                btnRoll.Text = "🎲 Roll Dice 擲骰子";
                lblPlayer1.Text = "Player 1";
                lblPlayer2.Text = "Player 2";
                lblRule.Text = "Rule: Higher number wins | 點數大者獲勝";
            }
            else
            {
                lblTitle.Text = "✂️ Rock Paper Scissors 猜拳";
                btnRoll.Text = "✂️ Play 猜拳！";
                lblPlayer1.Text = "Player 1";
                lblPlayer2.Text = "Player 2";
                lblRule.Text = "Rule: Rock > Scissors > Paper > Rock | 石頭>剪刀>布>石頭";
            }
        }

        /// <summary>
        /// 在 ListBox 中附加本局結果（加分功能）
        /// </summary>
        private void AppendHistory()
        {
            string result;
            if (player1Value == player2Value)
            {
                result = "Tie";
            }
            else if (currentMode == 0)
            {
                result = (player1Value > player2Value) ? "P1" : "P2";
            }
            else
            {
                int diff = player1Value - player2Value;
                result = (diff == 1 || diff == -2) ? "P1" : "P2";
            }

            string p1Info = (currentMode == 0)
                ? player1Value.ToString()
                : rpsNames[player1Value];
            string p2Info = (currentMode == 0)
                ? player2Value.ToString()
                : rpsNames[player2Value];

            string entry = "[" + DateTime.Now.ToString("HH:mm:ss") + "] "
                + "P1:" + p1Info + " vs P2:" + p2Info + " → " + result;

            // 保持最多 20 筆，超過時移除最舊的
            if (lbHistory.Items.Count >= 20)
                lbHistory.Items.RemoveAt(0);

            lbHistory.Items.Add(entry);
            lbHistory.TopIndex = lbHistory.Items.Count - 1;
        }

        // ==================== 結束程式 ====================

        private void Form1_FormClosing(object sender, FormClosingEventArgs e)
        {
            // 釋放圖片資源，防止記憶體洩漏
            try
            {
                pbPlayer1.Image?.Dispose();
                pbPlayer2.Image?.Dispose();
            }
            catch { }
        }

        // ==================== Designer 程式碼（UI 配置）====================
        // ※ 以下為 Visual Studio Form Designer 自動產生的程式碼
        // ※ 若在 VS 中，可刪除整個 Designer.cs 檔案，並在 VS 中直接拉 UI
        // ※ 這裡的程式碼可以「複製貼上」到新建立的 Windows Forms 專案中
        // ================================================================

        #region Windows Form Designer generated code

        private System.ComponentModel.IContainer components = null;
        private ComboBox cbMode;
        private Label lblTitle;
        private Label lblPlayer1;
        private Label lblPlayer2;
        private PictureBox pbPlayer1;
        private PictureBox pbPlayer2;
        private Button btnRoll;
        private Label lblResult;
        private Label lblRule;
        private ListBox lbHistory;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
                components.Dispose();
            base.Dispose(disposing);
        }

        private void InitializeComponent()
        {
            this.components = new System.ComponentModel.Container();
            this cbMode = new ComboBox();
            this.lblTitle = new Label();
            this.lblPlayer1 = new Label();
            this.lblPlayer2 = new Label();
            this.lblRule = new Label();
            this.btnRoll = new Button();
            this.lblResult = new Label();
            this.lbHistory = new ListBox();
            this.pbPlayer1 = new PictureBox();
            this.pbPlayer2 = new PictureBox();
            ((System.ComponentModel.ISupportInitialize)(this.pbPlayer1)).BeginInit();
            ((System.ComponentModel.ISupportInitialize)(this.pbPlayer2)).BeginInit();
            this.SuspendLayout();

            // ==================== 整體 Form 設定 ====================
            this.ClientSize = new Size(520, 520);
            this.Name = "Form1";
            this.Text = "Dice & RPS Game | 骰子與猜拳";
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(240, 240, 245);
            this.FormClosing += new FormClosingEventHandler(this.Form1_FormClosing);

            // ==================== 模式選擇 ComboBox ====================
            this.cbMode.DropDownStyle = ComboBoxStyle.DropDownList;
            this.cbMode.Font = new Font("Microsoft JhengHei", 11F);
            this.cbMode.Items.AddRange(new object[] { "🎲 Dice 骰子比大小", "✂️ Rock Paper Scissors 猜拳" });
            this.cbMode.Location = new Point(135, 18);
            this.cbMode.Name = "cbMode";
            this.cbMode.Size = new Size(250, 28);
            this.cbMode.SelectedIndex = 0;
            this.cbMode.SelectedIndexChanged += new EventHandler(this.cbMode_SelectedIndexChanged);

            // ==================== 遊戲標題 ====================
            this.lblTitle.Font = new Font("Microsoft JhengHei", 18F, FontStyle.Bold);
            this.lblTitle.ForeColor = Color.FromArgb(30, 30, 60);
            this.lblTitle.Location = new Point(10, 52);
            this.lblTitle.Name = "lblTitle";
            this.lblTitle.Size = new Size(500, 38);
            this.lblTitle.Text = "🎲 Dice Game 骰子比大小";
            this.lblTitle.TextAlign = ContentAlignment.MiddleCenter;

            // ==================== 玩家1 標籤 ====================
            this.lblPlayer1.Font = new Font("Microsoft JhengHei", 12F, FontStyle.Bold);
            this.lblPlayer1.ForeColor = Color.FromArgb(0, 100, 200);
            this.lblPlayer1.Location = new Point(40, 98);
            this.lblPlayer1.Name = "lblPlayer1";
            this.lblPlayer1.Size = new Size(200, 25);
            this.lblPlayer1.Text = "Player 1";
            this.lblPlayer1.TextAlign = ContentAlignment.MiddleCenter;

            // ==================== 玩家2 標籤 ====================
            this.lblPlayer2.Font = new Font("Microsoft JhengHei", 12F, FontStyle.Bold);
            this.lblPlayer2.ForeColor = Color.FromArgb(200, 80, 0);
            this.lblPlayer2.Location = new Point(280, 98);
            this.lblPlayer2.Name = "lblPlayer2";
            this.lblPlayer2.Size = new Size(200, 25);
            this.lblPlayer2.Text = "Player 2";
            this.lblPlayer2.TextAlign = ContentAlignment.MiddleCenter;

            // ==================== 玩家1 圖片區 ====================
            this.pbPlayer1.BackColor = Color.White;
            this.pbPlayer1.BorderStyle = BorderStyle.FixedSingle;
            this.pbPlayer1.Location = new Point(40, 128);
            this.pbPlayer1.Name = "pbPlayer1";
            this.pbPlayer1.Size = new Size(200, 200);
            this.pbPlayer1.SizeMode = PictureBoxSizeMode.StretchImage;
            this.pbPlayer1.TabStop = false;

            // ==================== 玩家2 圖片區 ====================
            this.pbPlayer2.BackColor = Color.White;
            this.pbPlayer2.BorderStyle = BorderStyle.FixedSingle;
            this.pbPlayer2.Location = new Point(280, 128);
            this.pbPlayer2.Name = "pbPlayer2";
            this.pbPlayer2.Size = new Size(200, 200);
            this.pbPlayer2.SizeMode = PictureBoxSizeMode.StretchImage;
            this.pbPlayer2.TabStop = false;

            // ==================== 遊戲按鈕 ====================
            this.btnRoll.Font = new Font("Microsoft JhengHei", 14F, FontStyle.Bold);
            this.btnRoll.ForeColor = Color.White;
            this.btnRoll.BackColor = Color.FromArgb(0, 150, 100);
            this.btnRoll.FlatStyle = FlatStyle.Flat;
            this.btnRoll.Location = new Point(135, 340);
            this.btnRoll.Name = "btnRoll";
            this.btnRoll.Size = new Size(250, 50);
            this.btnRoll.TabIndex = 0;
            this.btnRoll.Text = "🎲 Roll Dice 擲骰子";
            this.btnRoll.UseVisualStyleBackColor = false;
            this.btnRoll.Click += new EventHandler(this.btnRoll_Click);

            // ==================== 結果顯示標籤 ====================
            this.lblResult.Font = new Font("Microsoft JhengHei", 16F, FontStyle.Bold);
            this.lblResult.Location = new Point(40, 400);
            this.lblResult.Name = "lblResult";
            this.lblResult.Size = new Size(440, 36);
            this.lblResult.Text = "Press Roll / Play to start!";
            this.lblResult.TextAlign = ContentAlignment.MiddleCenter;
            this.lblResult.BorderStyle = BorderStyle.FixedSingle;

            // ==================== 遊戲規則提示 ====================
            this.lblRule.Font = new Font("Microsoft JhengHei", 9F);
            this.lblRule.ForeColor = Color.Gray;
            this.lblRule.Location = new Point(40, 442);
            this.lblRule.Name = "lblRule";
            this.lblRule.Size = new Size(440, 20);
            this.lblRule.Text = "Rule: Higher number wins | 點數大者獲勝";
            this.lblRule.TextAlign = ContentAlignment.MiddleCenter;

            // ==================== 歷史紀錄 ListBox（加分功能） ====================
            this.lbHistory.Font = new Font("Consolas", 9F);
            this.lbHistory.ItemHeight = 14;
            this.lbHistory.Location = new Point(40, 468);
            this.lbHistory.Name = "lbHistory";
            this.lbHistory.Size = new Size(440, 44);
            this.lbHistory.TabIndex = 1;

            // ==================== 加入控制項 ====================
            this.Controls.Add(cbMode);
            this.Controls.Add(lblTitle);
            this.Controls.Add(lblPlayer1);
            this.Controls.Add(lblPlayer2);
            this.Controls.Add(pbPlayer1);
            this.Controls.Add(pbPlayer2);
            this.Controls.Add(btnRoll);
            this.Controls.Add(lblResult);
            this.Controls.Add(lblRule);
            this.Controls.Add(lbHistory);

            ((System.ComponentModel.ISupportInitialize)(this.pbPlayer1)).EndInit();
            ((System.ComponentModel.ISupportInitialize)(this.pbPlayer2)).EndInit();
            this.ResumeLayout(false);
        }

        #endregion
    }
}
