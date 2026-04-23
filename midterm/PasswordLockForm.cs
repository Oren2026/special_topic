using System;
using System.Drawing;
using System.Windows.Forms;

namespace MidtermExam
{
    public class PasswordLockForm : Form
    {
        private TextBox txtDisplay;
        private string inputPassword = "";
        private string correctPassword = "0504";
        
        public PasswordLockForm()
        {
            this.Text = "密碼鎖 - 期中考";
            this.Size = new Size(350, 450);
            this.StartPosition = FormStartPosition.CenterScreen;
            
            InitializeDisplay();
            InitializeNumberPad();
            InitializeClearButton();
        }
        
        private void InitializeDisplay()
        {
            txtDisplay = new TextBox();
            txtDisplay.Location = new Point(30, 30);
            txtDisplay.Size = new Size(280, 30);
            txtDisplay.Font = new Font("Consolas", 16);
            txtDisplay.TextAlign = HorizontalAlignment.Center;
            txtDisplay.ReadOnly = true;
            txtDisplay.Text = "****";
            this.Controls.Add(txtDisplay);
        }
        
        private void InitializeNumberPad()
        {
            int[] btnTags = { 1, 2, 3, 4, 5, 6, 7, 8, 9, -1, 0, -1 };
            
            for (int i = 0; i < 12; i++)
            {
                if (btnTags[i] == -1) continue;
                
                Button btn = new Button();
                btn.Text = btnTags[i].ToString();
                btn.Tag = btnTags[i];
                btn.Size = new Size(70, 50);
                
                int row = i / 3;
                int col = i % 3;
                btn.Location = new Point(30 + col * 85, 80 + row * 60);
                btn.Click += NumberBtn_Click;
                this.Controls.Add(btn);
            }
        }
        
        private void InitializeClearButton()
        {
            Button btnClear = new Button();
            btnClear.Text = "C. 清空";
            btnClear.Location = new Point(30, 320);
            btnClear.Size = new Size(280, 40);
            btnClear.Click += BtnClear_Click;
            this.Controls.Add(btnClear);
        }
        
        private void NumberBtn_Click(object sender, EventArgs e)
        {
            if (inputPassword.Length >= 4) return;
            
            Button btn = (Button)sender;
            int num = (int)btn.Tag;
            inputPassword += num.ToString();
            txtDisplay.Text = inputPassword.PadRight(4, '*').Substring(0, 4);
            
            if (inputPassword.Length == 4)
            {
                if (inputPassword == correctPassword)
                {
                    txtDisplay.Text = "success";
                    txtDisplay.ForeColor = Color.Green;
                }
                else
                {
                    txtDisplay.Text = "error";
                    txtDisplay.ForeColor = Color.Red;
                }
            }
        }
        
        private void BtnClear_Click(object sender, EventArgs e)
        {
            inputPassword = "";
            txtDisplay.Text = "****";
            txtDisplay.ForeColor = Color.Black;
        }
    }
}
