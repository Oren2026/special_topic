using System;
using System.Drawing;
using System.Windows.Forms;

namespace MidtermExam
{
    public class MatrixForm : Form
    {
        private TextBox txtA, txtB, txtC;
        private Label lblX, lblY;
        
        public MatrixForm()
        {
            this.Text = "矩陣運算 - 期中考";
            this.Size = new Size(400, 350);
            this.StartPosition = FormStartPosition.CenterScreen;
            CreateMatrixUI();
        }
        
        private void CreateMatrixUI()
        {
            // 左側矩陣 [√□  4]  [ 8   □]
            
            Label lblRoot = new Label();
            lblRoot.Text = "√";
            lblRoot.Font = new Font("Times New Roman", 16);
            lblRoot.Location = new Point(30, 50);
            lblRoot.AutoSize = true;
            this.Controls.Add(lblRoot);
            
            txtA = new TextBox();
            txtA.Location = new Point(50, 50);
            txtA.Size = new Size(40, 25);
            this.Controls.Add(txtA);
            
            Label lblPlus1 = new Label();
            lblPlus1.Text = "4";
            lblPlus1.Location = new Point(100, 50);
            lblPlus1.AutoSize = true;
            this.Controls.Add(lblPlus1);
            
            Label lbl8 = new Label();
            lbl8.Text = "8";
            lbl8.Location = new Point(30, 90);
            lbl8.AutoSize = true;
            this.Controls.Add(lbl8);
            
            txtB = new TextBox();
            txtB.Location = new Point(50, 85);
            txtB.Size = new Size(40, 25);
            this.Controls.Add(txtB);
            
            Label lblTimes = new Label();
            lblTimes.Text = "×";
            lblTimes.Location = new Point(130, 70);
            lblTimes.AutoSize = true;
            this.Controls.Add(lblTimes);
            
            // 中間矩陣 [3  □]  [1  2]
            
            Label lbl3 = new Label();
            lbl3.Text = "3";
            lbl3.Location = new Point(160, 50);
            lbl3.AutoSize = true;
            this.Controls.Add(lbl3);
            
            txtC = new TextBox();
            txtC.Location = new Point(180, 50);
            txtC.Size = new Size(40, 25);
            this.Controls.Add(txtC);
            
            Label lbl1 = new Label();
            lbl1.Text = "1";
            lbl1.Location = new Point(160, 90);
            lbl1.AutoSize = true;
            this.Controls.Add(lbl1);
            
            Label lbl2 = new Label();
            lbl2.Text = "2";
            lbl2.Location = new Point(200, 90);
            lbl2.AutoSize = true;
            this.Controls.Add(lbl2);
            
            Label lblEqual = new Label();
            lblEqual.Text = "=";
            lblEqual.Location = new Point(250, 70);
            lblEqual.AutoSize = true;
            this.Controls.Add(lblEqual);
            
            lblX = new Label();
            lblX.Text = "x";
            lblX.Location = new Point(280, 50);
            lblX.AutoSize = true;
            this.Controls.Add(lblX);
            
            lblY = new Label();
            lblY.Text = "y";
            lblY.Location = new Point(280, 90);
            lblY.AutoSize = true;
            this.Controls.Add(lblY);
            
            Button btnCalc = new Button();
            btnCalc.Text = "計算 x, y";
            btnCalc.Location = new Point(140, 150);
            btnCalc.Size = new Size(100, 35);
            btnCalc.Click += BtnCalc_Click;
            this.Controls.Add(btnCalc);
        }
        
        private void BtnCalc_Click(object sender, EventArgs e)
        {
            try
            {
                double a = double.Parse(txtA.Text);
                double b = double.Parse(txtB.Text);
                double x = a * 3 + 4 * 1;
                double y = 8 * 3 + b * 1;
                lblX.Text = x.ToString();
                lblY.Text = y.ToString();
            }
            catch
            {
                MessageBox.Show("請輸入有效的數字！");
            }
        }
    }
}
