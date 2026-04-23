using System;
using System.Drawing;
using System.Text.RegularExpressions;
using System.Windows.Forms;

namespace MidtermExam
{
    public class PasswordStrengthForm : Form
    {
        private TextBox txtPassword;
        
        public PasswordStrengthForm()
        {
            this.Text = "密碼強度 - 期中考";
            this.Size = new Size(350, 200);
            this.StartPosition = FormStartPosition.CenterScreen;
            
            Label lblPassword = new Label();
            lblPassword.Text = "請輸入密碼：";
            lblPassword.Location = new Point(30, 30);
            lblPassword.AutoSize = true;
            this.Controls.Add(lblPassword);
            
            txtPassword = new TextBox();
            txtPassword.Location = new Point(30, 55);
            txtPassword.Size = new Size(280, 25);
            txtPassword.PasswordChar = '*';
            this.Controls.Add(txtPassword);
            
            Button btnConfirm = new Button();
            btnConfirm.Text = "確認密碼";
            btnConfirm.Location = new Point(120, 95);
            btnConfirm.Size = new Size(100, 35);
            btnConfirm.Click += BtnConfirm_Click;
            this.Controls.Add(btnConfirm);
        }
        
        private void BtnConfirm_Click(object sender, EventArgs e)
        {
            string password = txtPassword.Text;
            bool isValid = true;
            string errorMsg = "";
            
            if (password.Length < 5)
            {
                isValid = false;
                errorMsg += "密碼長度至少5碼\n";
            }
            if (!Regex.IsMatch(password, "[A-Z]"))
            {
                isValid = false;
                errorMsg += "至少一個大寫英文\n";
            }
            if (!Regex.IsMatch(password, "[a-z]"))
            {
                isValid = false;
                errorMsg += "至少一個小寫英文\n";
            }
            if (!Regex.IsMatch(password, "[0-9]"))
            {
                isValid = false;
                errorMsg += "至少一個數字\n";
            }
            
            if (isValid)
                MessageBox.Show("通過", "密碼強度檢測");
            else
                MessageBox.Show("密碼強度不足\n" + errorMsg, "密碼強度檢測");
        }
    }
}
