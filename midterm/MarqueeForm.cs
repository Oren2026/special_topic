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
        
        // 位置：0=上, 1=右, 2=下, 3=左 (順時鐘順序)
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
                labels[i].Font = new Font("微軟正黑體", 28, FontStyle.Bold);
                labels[i].AutoSize = true;
                labels[i].BackColor = Color.White;
                labels[i].Padding = new Padding(10);
                this.Controls.Add(labels[i]);
            }
        }
        
        private void InitializeButtons()
        {
            Button btnLeft = new Button();
            btnLeft.Text = "◀ 左轉 (逆時鐘)";
            btnLeft.Size = new Size(140, 45);
            btnLeft.Location = new Point(80, 280);
            btnLeft.Font = new Font("微軟正黑體", 10);
            btnLeft.Click += BtnLeft_Click;
            this.Controls.Add(btnLeft);
            
            Button btnRight = new Button();
            btnRight.Text = "右轉 (順時鐘) ▶";
            btnRight.Size = new Size(140, 45);
            btnRight.Location = new Point(260, 280);
            btnRight.Font = new Font("微軟正黑體", 10);
            btnRight.Click += BtnRight_Click;
            this.Controls.Add(btnRight);
        }
        
        private void UpdateLabelPositions()
        {
            // 上下左右四個位置
            // 上(北): 正上方, 右(東): 右側, 下(南): 下方, 左(西): 左側
            Point[] points = {
                new Point(220, 30),   // 上 - 北
                new Point(420, 140),  // 右 - 東
                new Point(220, 250),  // 下 - 南
                new Point(20, 140)    // 左 - 西
            };
            
            for (int i = 0; i < 4; i++)
            {
                labels[positions[i]].Location = points[i];
            }
        }
        
        // A. 左轉：逆時鐘轉動 (北→西→南→東→北)
        // positions[0]=上, [1]=右, [2]=下, [3]=左
        // 逆時針：上→左→下→右→上 (index: 0→3→2→1→0)
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
        
        // B. 右轉：順時鐘轉動 (北→東→南→西→北)
        // 順時針：上→右→下→左→上 (index: 0→1→2→3→0)
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
