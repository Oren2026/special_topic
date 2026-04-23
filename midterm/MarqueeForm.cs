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
        
        // 四個定點座標
        private Point[] targetPoints;
        
        // 動畫用
        private System.Windows.Forms.Timer animationTimer;
        private int animationFrame = 0;
        private int totalFrames = 8;
        private Point[][] framePositions;  // 每幀每個label的位置
        private bool isAnimating = false;
        
        public MarqueeForm()
        {
            this.Text = "跑馬燈 - 期中考";
            this.Size = new Size(420, 450);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(240, 235, 224);  // 溫暖米白背景
            
            // 四個定點座標（上下左右）
            targetPoints = new Point[] {
                new Point(170, 40),    // 上 - 北
                new Point(320, 150),   // 右 - 東
                new Point(170, 260),   // 下 - 南
                new Point(20, 150)      // 左 - 西
            };
            
            animationTimer = new System.Windows.Forms.Timer();
            animationTimer.Interval = 30;
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
                labels[i].Font = new Font("Microsoft JhengHei", 32, FontStyle.Bold);
                labels[i].AutoSize = false;
                labels[i].Size = new Size(80, 80);
                labels[i].TextAlign = ContentAlignment.MiddleCenter;
                labels[i].BackColor = Color.White;
                labels[i].FlatStyle = FlatStyle.Flat;
                labels[i].BorderStyle = BorderStyle.FixedSingle;
                labels[i].Cursor = Cursors.Hand;
                
                // 加入陰影效果
                labels[i].Paint += Label_Paint;
                this.Controls.Add(labels[i]);
            }
        }
        
        private void Label_Paint(object sender, PaintEventArgs e)
        {
            Label lbl = sender as Label;
            if (lbl == null) return;
            
            // 簡單陰影
            using (Pen pen = new Pen(Color.FromArgb(50, 0, 0, 0), 2))
            {
                Rectangle rect = new Rectangle(lbl.Left + 3, lbl.Top + 3, lbl.Width, lbl.Height);
                e.Graphics.DrawRectangle(pen, rect);
            }
        }
        
        private void InitializeButtons()
        {
            Button btnLeft = new Button();
            btnLeft.Text = "◀ 左轉";
            btnLeft.Size = new Size(120, 45);
            btnLeft.Location = new Point(70, 380);
            btnLeft.Font = new Font("Microsoft JhengHei", 12, FontStyle.Bold);
            btnLeft.BackColor = Color.FromArgb(70, 130, 180);  //  SteelBlue
            btnLeft.ForeColor = Color.White;
            btnLeft.FlatStyle = FlatStyle.Flat;
            btnLeft.FlatAppearance.BorderSize = 0;
            btnLeft.Click += BtnLeft_Click;
            this.Controls.Add(btnLeft);
            
            Button btnRight = new Button();
            btnRight.Text = "右轉 ▶";
            btnRight.Size = new Size(120, 45);
            btnRight.Location = new Point(220, 380);
            btnRight.Font = new Font("Microsoft JhengHei", 12, FontStyle.Bold);
            btnRight.BackColor = Color.FromArgb(205, 133, 63);  //  Peru / 棕色
            btnRight.ForeColor = Color.White;
            btnRight.FlatStyle = FlatStyle.Flat;
            btnRight.FlatAppearance.BorderSize = 0;
            btnRight.Click += BtnRight_Click;
            this.Controls.Add(btnRight);
        }
        
        private Point[] GetStartPositions()
        {
            Point[] starts = new Point[4];
            for (int i = 0; i < 4; i++)
            {
                starts[positions[i]] = targetPoints[i];
            }
            return starts;
        }
        
        private Point[] GetEndPositions(int[] newPositions)
        {
            Point[] ends = new Point[4];
            for (int i = 0; i < 4; i++)
            {
                ends[newPositions[i]] = targetPoints[i];
            }
            return ends;
        }
        
        private void UpdateLabelPositions()
        {
            for (int i = 0; i < 4; i++)
            {
                labels[positions[i]].Location = targetPoints[i];
            }
        }
        
        // 計算兩點之間的中間點
        private Point MidPoint(Point p1, Point p2, float t)
        {
            return new Point(
                (int)(p1.X + (p2.X - p1.X) * t),
                (int)(p1.Y + (p2.Y - p1.Y) * t)
            );
        }
        
        // 計算動畫幀
        private void PrepareAnimationFrames(Point[] startPos, Point[] endPos)
        {
            framePositions = new Point[totalFrames + 1][];
            
            for (int frame = 0; frame <= totalFrames; frame++)
            {
                float t = (float)frame / totalFrames;
                // 使用 easeInOut 曲線讓動畫更平滑
                float easedT = EaseInOut(t);
                
                framePositions[frame] = new Point[4];
                for (int i = 0; i < 4; i++)
                {
                    framePositions[frame][i] = MidPoint(startPos[i], endPos[i], easedT);
                }
            }
        }
        
        // 緩入緩出曲線
        private float EaseInOut(float t)
        {
            return t < 0.5f 
                ? 2 * t * t 
                : -1 + (4 - 2 * t) * t;
        }
        
        private void StartAnimation()
        {
            if (isAnimating) return;
            isAnimating = true;
            animationFrame = 0;
            animationTimer.Start();
        }
        
        private void AnimationTimer_Tick(object sender, EventArgs e)
        {
            animationFrame++;
            
            if (animationFrame <= totalFrames)
            {
                // 更新每個label的位置
                for (int i = 0; i < 4; i++)
                {
                    labels[i].Location = framePositions[animationFrame][i];
                }
            }
            else
            {
                // 動畫結束
                animationTimer.Stop();
                isAnimating = false;
            }
        }
        
        // 左轉：逆時鐘轉動
        private void BtnLeft_Click(object sender, EventArgs e)
        {
            if (isAnimating) return;
            
            // 儲存動畫前的位置
            Point[] startPos = GetStartPositions();
            
            // 計算新位置（逆時針）
            int[] newPositions = (int[])positions.Clone();
            int last = newPositions[3];
            for (int i = 3; i > 0; i--)
            {
                newPositions[i] = newPositions[i - 1];
            }
            newPositions[0] = last;
            
            // 計算動畫幀
            Point[] endPos = GetEndPositions(newPositions);
            PrepareAnimationFrames(startPos, endPos);
            
            // 更新邏輯位置
            positions = newPositions;
            
            // 開始動畫
            StartAnimation();
        }
        
        // 右轉：順時鐘轉動
        private void BtnRight_Click(object sender, EventArgs e)
        {
            if (isAnimating) return;
            
            Point[] startPos = GetStartPositions();
            
            int[] newPositions = (int[])positions.Clone();
            int first = newPositions[0];
            for (int i = 0; i < 3; i++)
            {
                newPositions[i] = newPositions[i + 1];
            }
            newPositions[3] = first;
            
            Point[] endPos = GetEndPositions(newPositions);
            PrepareAnimationFrames(startPos, endPos);
            
            positions = newPositions;
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
