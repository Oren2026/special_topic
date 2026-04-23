using System;
using System.Drawing;
using System.Windows.Forms;

namespace MidtermExam
{
    public class MarqueeForm : Form
    {
        private Label[] labels = new Label[4];
        // 東(紅)、南(綠)、西(藍)、北(黑)
        private string[] texts = { "東", "南", "西", "北" };
        private Color[] colors = { Color.Red, Color.Green, Color.Blue, Color.Black };
        // 位置：0=右下, 1=左下, 2=左上, 3=右上
        private int[] positions = { 0, 1, 2, 3 };
        
        public MarqueeForm()
        {
            this.Text = "跑馬燈 - 期中考";
            this.Size = new Size(500, 350);
            this.StartPosition = FormStartPosition.CenterScreen;
            
            InitializeLabels();
            InitializeButtons();
            UpdateLabelPositions();
        }
        
        private void InitializeLabels()
        {
            for (int i = 0; i < 4; i++)
            {
                labels[i] = new Label();
                labels[i].Text = texts[i];
                labels[i].ForeColor = colors[i];
                labels[i].Font = new Font("微軟正黑體", 24, FontStyle.Bold);
                labels[i].AutoSize = true;
                this.Controls.Add(labels[i]);
            }
        }
        
        private void InitializeButtons()
        {
            Button btnLeft = new Button();
            btnLeft.Text = "◀ 左轉";
            btnLeft.Size = new Size(100, 40);
            btnLeft.Location = new Point(100, 280);
            btnLeft.Click += BtnLeft_Click;
            this.Controls.Add(btnLeft);
            
            Button btnRight = new Button();
            btnRight.Text = "右轉 ▶";
            btnRight.Size = new Size(100, 40);
            btnRight.Location = new Point(280, 280);
            btnRight.Click += BtnRight_Click;
            this.Controls.Add(btnRight);
        }
        
        private void UpdateLabelPositions()
        {
            Point[] points = {
                new Point(280, 220),  // 右下 - 東(紅)
                new Point(20, 220),   // 左下 - 南(綠)
                new Point(20, 50),    // 左上 - 西(藍)
                new Point(280, 50)    // 右上 - 北(黑)
            };
            
            for (int i = 0; i < 4; i++)
            {
                labels[positions[i]].Location = points[i];
            }
        }
        
        // A. 左轉：逆時鐘轉動 (東→北→西→南→東)
        private void BtnLeft_Click(object sender, EventArgs e)
        {
            int last = positions[3];
            for (int i = 3; i > 0; i--)
            {
                positions[i] = positions[i - 1];
            }
            positions[0] = last;
            UpdateLabelPositions();
        }
        
        // B. 右轉：順時鐘轉動 (東→南→西→北→東)
        private void BtnRight_Click(object sender, EventArgs e)
        {
            int first = positions[0];
            for (int i = 0; i < 3; i++)
            {
                positions[i] = positions[i + 1];
            }
            positions[3] = first;
            UpdateLabelPositions();
        }
    }
}
