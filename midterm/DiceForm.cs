using System;
using System.Drawing;
using System.Windows.Forms;
using System.Random = System.Random;

namespace MidtermExam
{
    public class DiceForm : Form
    {
        private Label[] diceLabels = new Label[3];
        private Label lblScore;
        private Random rand = new Random();
        
        public DiceForm()
        {
            this.Text = "擲骰子 - 期中考";
            this.Size = new Size(400, 350);
            this.StartPosition = FormStartPosition.CenterScreen;
            
            InitializeDiceLabels();
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
            lblScore.Text = $"分數：{sum}";
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
            lblScore.Text = GetResultText(dice, score);
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
