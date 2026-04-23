using System;
using System.Drawing;
using System.Collections.Generic;
using System.Windows.Forms;

namespace MidtermExam
{
    public class DiceForm : Form
    {
        private Label[] diceLabels = new Label[3];
        private Label lblScore;                      // 大格顯示結果
        private ListBox lstHistory;                   // 紀錄列表
        private List<string> historyRecords;
        private Random rand = new Random();
        private int recordCounter;                    // 紀錄編號
        
        public DiceForm()
        {
            this.Text = "擲骰子 - 期中考";
            this.Size = new Size(620, 420);
            this.StartPosition = FormStartPosition.CenterScreen;
            
            historyRecords = new List<string>();
            recordCounter = 0;
            
            InitializeDiceLabels();
            InitializeScorePanel();
            InitializeHistoryPanel();
            InitializeButtons();
        }
        
        private void InitializeDiceLabels()
        {
            for (int i = 0; i < 3; i++)
            {
                diceLabels[i] = new Label();
                diceLabels[i].Text = "?";
                diceLabels[i].Font = new Font("Times New Roman", 42, FontStyle.Bold);
                diceLabels[i].Location = new Point(50 + i * 95, 40);
                diceLabels[i].Size = new Size(85, 85);
                diceLabels[i].TextAlign = ContentAlignment.MiddleCenter;
                diceLabels[i].BorderStyle = BorderStyle.FixedSingle;
                this.Controls.Add(diceLabels[i]);
            }
        }
        
        // 大的計分結果格子
        private void InitializeScorePanel()
        {
            lblScore = new Label();
            lblScore.Name = "lblScore";
            lblScore.Text = "等待擲骰子...";
            lblScore.Location = new Point(30, 140);
            lblScore.Size = new Size(340, 80);
            lblScore.TextAlign = ContentAlignment.MiddleCenter;
            lblScore.Font = new Font("微軟正黑體", 18, FontStyle.Bold);
            lblScore.BorderStyle = BorderStyle.FixedSingle;
            lblScore.BackColor = Color.White;
            this.Controls.Add(lblScore);
        }
        
        private void InitializeHistoryPanel()
        {
            // 紀錄標題
            Label lblHistoryTitle = new Label();
            lblHistoryTitle.Text = "📋 遊戲紀錄 (最近10筆)";
            lblHistoryTitle.Location = new Point(400, 30);
            lblHistoryTitle.Size = new Size(200, 25);
            lblHistoryTitle.Font = new Font("微軟正黑體", 11, FontStyle.Bold);
            this.Controls.Add(lblHistoryTitle);
            
            // 紀錄列表
            lstHistory = new ListBox();
            lstHistory.Location = new Point(400, 60);
            lstHistory.Size = new Size(200, 250);
            lstHistory.Font = new Font("Consolas", 10);
            this.Controls.Add(lstHistory);
        }
        
        private void InitializeButtons()
        {
            Button btnRoll = new Button();
            btnRoll.Name = "btnRoll";
            btnRoll.Text = "A. 擲三顆骰子 (總分)";
            btnRoll.Location = new Point(30, 240);
            btnRoll.Size = new Size(170, 45);
            btnRoll.Font = new Font("微軟正黑體", 10);
            btnRoll.Click += BtnRoll_Click;
            this.Controls.Add(btnRoll);
            
            Button btnGame = new Button();
            btnGame.Name = "btnGame";
            btnGame.Text = "B. 遊戲得分模式";
            btnGame.Location = new Point(210, 240);
            btnGame.Size = new Size(170, 45);
            btnGame.Font = new Font("微軟正黑體", 10);
            btnGame.Click += BtnGame_Click;
            this.Controls.Add(btnGame);
            
            Button btnClearHistory = new Button();
            btnClearHistory.Text = "C. 清空紀錄";
            btnClearHistory.Location = new Point(400, 320);
            btnClearHistory.Size = new Size(200, 35);
            btnClearHistory.Font = new Font("微軟正黑體", 10);
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
            
            lblScore.Text = $"【A模式】總分：{sum}";
            lblScore.BackColor = Color.LightBlue;
            
            recordCounter++;
            string record = $"#{recordCounter} [A] {dice[0]},{dice[1]},{dice[2]} → 總分 {sum}";
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
            string resultText = GetResultText(score);
            
            lblScore.Text = $"【B模式】{resultText}";
            lblScore.BackColor = Color.LightGreen;
            
            recordCounter++;
            string record = $"#{recordCounter} [B] {dice[0]},{dice[1]},{dice[2]} → {resultText}";
            AddToHistory(record);
        }
        
        private void BtnClearHistory_Click(object sender, EventArgs e)
        {
            historyRecords.Clear();
            lstHistory.Items.Clear();
            recordCounter = 0;
        }
        
        private void AddToHistory(string record)
        {
            historyRecords.Insert(0, record);
            
            if (historyRecords.Count > 10)
            {
                historyRecords.RemoveAt(historyRecords.Count - 1);
            }
            
            lstHistory.Items.Clear();
            for (int i = 0; i < historyRecords.Count; i++)
            {
                lstHistory.Items.Add(historyRecords[i]);
            }
        }
        
        private int CalculateGameScore(int[] dice)
        {
            if (dice[0] == dice[1] && dice[1] == dice[2])
                return -1;
            
            int[] sorted = (int[])dice.Clone();
            Array.Sort(sorted);
            if (sorted[0] == 1 && sorted[1] == 2 && sorted[2] == 3)
                return -2;
            
            if (dice[0] == dice[1]) return dice[2];
            if (dice[1] == dice[2]) return dice[0];
            if (dice[0] == dice[2]) return dice[1];
            
            return 0;
        }
        
        private string GetResultText(int score)
        {
            if (score == -1) return "豹子/一色！";
            if (score == -2) return "逼基！";
            if (score == 0)  return "0分 (三個都不同)";
            return $"得分：{score}";
        }
    }
}
