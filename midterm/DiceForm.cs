using System;
using System.Drawing;
using System.Collections.Generic;
using System.Windows.Forms;
using System.Random = System.Random;

namespace MidtermExam
{
    public class DiceForm : Form
    {
        private Label[] diceLabels = new Label[3];
        private Label lblScore;
        private ListBox lstHistory;          // 紀錄列表
        private List<string> historyRecords; // 儲存最近10筆紀錄
        private Random rand = new Random();
        
        public DiceForm()
        {
            this.Text = "擲骰子 - 期中考";
            this.Size = new Size(600, 350);  // 加寬視窗
            this.StartPosition = FormStartPosition.CenterScreen;
            
            historyRecords = new List<string>();
            
            InitializeDiceLabels();
            InitializeHistoryPanel();
            InitializeButtons();
        }
        
        private void InitializeDiceLabels()
        {
            for (int i = 0; i < 3; i++)
            {
                diceLabels[i] = new Label();
                diceLabels[i].Text = "?";
                diceLabels[i].Font = new Font("Times New Roman", 36, FontStyle.Bold);
                diceLabels[i].Location = new Point(60 + i * 100, 50);
                diceLabels[i].Size = new Size(80, 80);
                diceLabels[i].TextAlign = ContentAlignment.MiddleCenter;
                diceLabels[i].BorderStyle = BorderStyle.FixedSingle;
                this.Controls.Add(diceLabels[i]);
            }
            
            lblScore = new Label();
            lblScore.Text = "分數：0";
            lblScore.Location = new Point(130, 150);
            lblScore.AutoSize = true;
            lblScore.Font = new Font("微軟正黑體", 14);
            this.Controls.Add(lblScore);
        }
        
        private void InitializeHistoryPanel()
        {
            // 紀錄標題
            Label lblHistoryTitle = new Label();
            lblHistoryTitle.Text = "📋 最近10筆紀錄";
            lblHistoryTitle.Location = new Point(400, 30);
            lblHistoryTitle.Size = new Size(150, 25);
            lblHistoryTitle.Font = new Font("微軟正黑體", 11, FontStyle.Bold);
            this.Controls.Add(lblHistoryTitle);
            
            // 紀錄列表
            lstHistory = new ListBox();
            lstHistory.Location = new Point(400, 60);
            lstHistory.Size = new Size(170, 200);
            lstHistory.Font = new Font("Consolas", 10);
            this.Controls.Add(lstHistory);
        }
        
        private void InitializeButtons()
        {
            Button btnRoll = new Button();
            btnRoll.Text = "A. 擲三顆骰子";
            btnRoll.Location = new Point(50, 200);
            btnRoll.Size = new Size(130, 40);
            btnRoll.Click += BtnRoll_Click;
            this.Controls.Add(btnRoll);
            
            Button btnGame = new Button();
            btnGame.Text = "B. 遊戲得分";
            btnGame.Location = new Point(200, 200);
            btnGame.Size = new Size(130, 40);
            btnGame.Click += BtnGame_Click;
            this.Controls.Add(btnGame);
            
            // C. 清空紀錄按鈕
            Button btnClearHistory = new Button();
            btnClearHistory.Text = "C. 清空紀錄";
            btnClearHistory.Location = new Point(400, 270);
            btnClearHistory.Size = new Size(170, 35);
            btnClearHistory.Click += BtnClearHistory_Click;
            this.Controls.Add(btnClearHistory);
        }
        
        private void BtnRoll_Click(object sender, EventArgs e)
        {
            int[] dice = new int[3];
            int sum = 0;
            
            for (int i = 0; i < 3; i++)
            {
                dice[i] = rand.Next(1, 7);
                diceLabels[i].Text = dice[i].ToString();
                sum += dice[i];
            }
            
            string result = $"分數：{sum}";
            lblScore.Text = result;
            
            // 記錄：骰子[1,2,3] = 總分6
            string record = $"骰子[{dice[0]},{dice[1]},{dice[2]}] = 總分{sum}";
            AddToHistory(record);
        }
        
        private void BtnGame_Click(object sender, EventArgs e)
        {
            int[] dice = new int[3];
            
            for (int i = 0; i < 3; i++)
            {
                dice[i] = rand.Next(1, 7);
                diceLabels[i].Text = dice[i].ToString();
            }
            
            int score = CalculateGameScore(dice);
            string resultText = GetResultText(dice, score);
            lblScore.Text = resultText;
            
            // 記錄
            string record = $"骰子[{dice[0]},{dice[1]},{dice[2]}] → {resultText}";
            AddToHistory(record);
        }
        
        private void BtnClearHistory_Click(object sender, EventArgs e)
        {
            historyRecords.Clear();
            lstHistory.Items.Clear();
        }
        
        // 新增紀錄到歷史列表（最多10筆）
        private void AddToHistory(string record)
        {
            historyRecords.Insert(0, record);  // 最新的在上面
            
            // 保持最多10筆
            if (historyRecords.Count > 10)
            {
                historyRecords.RemoveAt(historyRecords.Count - 1);
            }
            
            // 更新顯示
            lstHistory.Items.Clear();
            for (int i = 0; i < historyRecords.Count; i++)
            {
                lstHistory.Items.Add($"{i + 1}. {historyRecords[i]}");
            }
        }
        
        private int CalculateGameScore(int[] dice)
        {
            // 豹子/一色：三個相同
            if (dice[0] == dice[1] && dice[1] == dice[2])
                return -1;
            
            // 逼基：123
            int[] sorted = (int[])dice.Clone();
            Array.Sort(sorted);
            if (sorted[0] == 1 && sorted[1] == 2 && sorted[2] == 3)
                return -2;
            
            // 兩個相同：扣除相同的，找出不同的當分數
            if (dice[0] == dice[1]) return dice[2];
            if (dice[1] == dice[2]) return dice[0];
            if (dice[0] == dice[2]) return dice[1];
            
            // 三個都不同 = 0分
            return 0;
        }
        
        private string GetResultText(int[] dice, int score)
        {
            if (score == -1) return "【豹子/一色】三個相同！";
            if (score == -2) return "【逼基】123！";
            if (score == 0)  return "【0分】三個點數不同";
            return $"【得分：{score}】";
        }
    }
}
