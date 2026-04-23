using System;
using System.Drawing;
using System.Windows.Forms;

namespace MidtermExam
{
    public class MarqueeForm : Form
    {
        private Label[] labels = new Label[4];
        private string[] texts = { "東", "南", "西", "北" };
        private Color[] colors = { Color.Red, Color.Green, Color.Blue, Color.Black };
        
        // 位置：0=上, 1=右, 2=下, 3=左 (順時鐘順序)
        private int[] positions = { 0, 1, 2, 3 };
        
        // 動畫用的計時器 (Windows.Forms.Timer 在 UI 執行緒上跑)
        private Timer animationTimer;
        private int animationStep = 0;
        private bool isAnimating = false;
        
        // 動畫狀態
        private float[] currentScales;
        private float pulseScale = 0.6f;
        
        public MarqueeForm()
        {
            this.Text = "跑馬燈 - 期中考";
            this.Size = new Size(400, 400);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(30, 30, 30);
            
            currentScales = new float[4];
            for (int i = 0; i < 4; i++) currentScales[i] = 1.0f;
            
            // Windows.Forms.Timer：每40ms更新一次動畫
            animationTimer = new Timer();
            animationTimer.Interval = 40;
            animationTimer.Tick += AnimationTimer_Tick;
            
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
                labels[i].Font = new Font("微軟正黑體", 36, FontStyle.Bold);
                labels[i].AutoSize = false;
                labels[i].Size = new Size(80, 80);
                labels[i].TextAlign = ContentAlignment.MiddleCenter;
                labels[i].BackColor = Color.FromArgb(50, 50, 50);
                labels[i].FlatStyle = FlatStyle.Flat;
                labels[i].BorderStyle = BorderStyle.FixedSingle;
                this.Controls.Add(labels[i]);
            }
        }
        
        private void InitializeButtons()
        {
            Button btnLeft = new Button();
            btnLeft.Text = "◀ 左轉 (逆時鐘)";
            btnLeft.Size = new Size(130, 45);
            btnLeft.Location = new Point(60, 330);
            btnLeft.Font = new Font("微軟正黑體", 11);
            btnLeft.BackColor = Color.FromArgb(60, 60, 60);
            btnLeft.ForeColor = Color.White;
            btnLeft.FlatStyle = FlatStyle.Flat;
            btnLeft.Click += BtnLeft_Click;
            this.Controls.Add(btnLeft);
            
            Button btnRight = new Button();
            btnRight.Text = "右轉 (順時鐘) ▶";
            btnRight.Size = new Size(130, 45);
            btnRight.Location = new Point(210, 330);
            btnRight.Font = new Font("微軟正黑體", 11);
            btnRight.BackColor = Color.FromArgb(60, 60, 60);
            btnRight.ForeColor = Color.White;
            btnRight.FlatStyle = FlatStyle.Flat;
            btnRight.Click += BtnRight_Click;
            this.Controls.Add(btnRight);
        }
        
        private Point[] GetTargetPositions()
        {
            return new Point[] {
                new Point(160, 30),   // 上 - 北
                new Point(300, 150),  // 右 - 東
                new Point(160, 260),  // 下 - 南
                new Point(20, 150)    // 左 - 西
            };
        }
        
        private void UpdateLabelPositions()
        {
            Point[] points = GetTargetPositions();
            for (int i = 0; i < 4; i++)
            {
                labels[positions[i]].Location = points[i];
            }
        }
        
        private void UpdateLabelScales()
        {
            for (int i = 0; i < 4; i++)
            {
                float scale = currentScales[i];
                int baseSize = 36;
                int fontSize = (int)(baseSize * scale);
                if (fontSize < 8) fontSize = 8;
                labels[i].Font = new Font("微軟正黑體", fontSize, FontStyle.Bold);
                
                // 調整透明度配合動畫
                int alpha = (int)(120 + 135 * scale);
                if (alpha > 255) alpha = 255;
                labels[i].ForeColor = Color.FromArgb(alpha, colors[i]);
            }
        }
        
        private void StartAnimation()
        {
            if (isAnimating) return;
            isAnimating = true;
            animationStep = 0;
            animationTimer.Start();
        }
        
        private void AnimationTimer_Tick(object sender, EventArgs e)
        {
            animationStep++;
            
            if (animationStep <= 4)
            {
                // 第一階段：縮小
                float t = animationStep / 4f;
                for (int i = 0; i < 4; i++)
                {
                    currentScales[i] = 1.0f - (1.0f - pulseScale) * t;
                }
            }
            else if (animationStep <= 8)
            {
                // 第二階段：放大回來
                float t = (animationStep - 4) / 4f;
                for (int i = 0; i < 4; i++)
                {
                    currentScales[i] = pulseScale + (1.0f - pulseScale) * t;
                }
            }
            else
            {
                // 完成動畫
                animationTimer.Stop();
                isAnimating = false;
                for (int i = 0; i < 4; i++)
                {
                    currentScales[i] = 1.0f;
                }
            }
            
            UpdateLabelScales();
        }
        
        // 左轉：逆時鐘轉動
        private void BtnLeft_Click(object sender, EventArgs e)
        {
            if (isAnimating) return;
            
            int last = positions[3];
            for (int i = 3; i > 0; i--)
            {
                positions[i] = positions[i - 1];
            }
            positions[0] = last;
            
            UpdateLabelPositions();
            StartAnimation();
        }
        
        // 右轉：順時鐘轉動
        private void BtnRight_Click(object sender, EventArgs e)
        {
            if (isAnimating) return;
            
            int first = positions[0];
            for (int i = 0; i < 3; i++)
            {
                positions[i] = positions[i + 1];
            }
            positions[3] = first;
            
            UpdateLabelPositions();
            StartAnimation();
        }
        
        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            animationTimer.Stop();
            animationTimer.Dispose();
            base.OnFormClosed(e);
        }
    }
}
