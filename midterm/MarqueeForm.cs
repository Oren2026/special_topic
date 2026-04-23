using System;
using System.Drawing;
using System.Windows.Forms;
using SystemTimer = System.Timers.Timer;

namespace MidtermExam
{
    public class MarqueeForm : Form
    {
        private Label[] labels = new Label[4];
        private string[] texts = { "東", "南", "西", "北" };
        private Color[] colors = { Color.Red, Color.Green, Color.Blue, Color.Black };
        
        // 位置：0=上, 1=右, 2=下, 3=左 (順時鐘順序)
        private int[] positions = { 0, 1, 2, 3 };
        
        // 動畫用的計時器
        private SystemTimer animationTimer;
        private int animationStep = 0;
        private bool isAnimating = false;
        
        // 動畫狀態
        private float[] currentScales;  // 每個標籤目前的縮放
        private float targetScale = 1.0f;
        private float pulseScale = 0.5f;  // 動畫時縮小到50%
        
        public MarqueeForm()
        {
            this.Text = "跑馬燈 - 期中考";
            this.Size = new Size(400, 400);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(30, 30, 30);
            
            currentScales = new float[4];
            for (int i = 0; i < 4; i++) currentScales[i] = 1.0f;
            
            // 動畫計時器：每30ms更新一次
            animationTimer = new SystemTimer();
            animationTimer.Interval = 30;
            animationTimer.Elapsed += AnimationTimer_Tick;
            
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
                labels[i].BorderColor = colors[i];
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
            // 上下左右四個位置（更靠近中心）
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
                // 使用 Font 的縮放效果：改變字體大小
                int baseSize = 36;
                int fontSize = (int)(baseSize * scale);
                if (fontSize < 10) fontSize = 10;
                labels[i].Font = new Font("微軟正黑體", fontSize, FontStyle.Bold);
                
                // 調整透明度配合動畫
                int alpha = (int)(150 + 105 * scale);
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
            
            if (animationStep <= 5)
            {
                // 第一階段：縮小（所有標籤一起縮小）
                float t = animationStep / 5f;
                for (int i = 0; i < 4; i++)
                {
                    currentScales[i] = 1.0f - (1.0f - pulseScale) * t;
                }
            }
            else if (animationStep == 6)
            {
                // 第二階段：中間點，換位置
                if (sender is SystemTimer) { }
                // 已經在事件處理前換位置了，這裡不做額外事
            }
            else if (animationStep <= 11)
            {
                // 第三階段：恢復（所有標籤一起放大）
                float t = (animationStep - 6) / 5f;
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
        
        // 左轉：逆時鐘轉動 (北→西→南→東→北)
        private void BtnLeft_Click(object sender, EventArgs e)
        {
            if (isAnimating) return;
            
            // 先換位置
            int last = positions[3];
            for (int i = 3; i > 0; i--)
            {
                positions[i] = positions[i - 1];
            }
            positions[0] = last;
            
            // 啟動動畫
            StartAnimation();
            UpdateLabelPositions();
        }
        
        // 右轉：順時鐘轉動 (北→東→南→西→北)
        private void BtnRight_Click(object sender, EventArgs e)
        {
            if (isAnimating) return;
            
            // 先換位置
            int first = positions[0];
            for (int i = 0; i < 3; i++)
            {
                positions[i] = positions[i + 1];
            }
            positions[3] = first;
            
            // 啟動動畫
            StartAnimation();
            UpdateLabelPositions();
        }
        
        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            animationTimer.Stop();
            animationTimer.Dispose();
            base.OnFormClosed(e);
        }
    }
}
