using System;
using System.Windows.Forms;

namespace MidtermExam
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            
            // 選擇要執行的題目：
            Application.Run(new MarqueeForm());       // 第1題 - 跑馬燈
            // Application.Run(new MatrixForm());        // 第2題 - 矩陣運算
            // Application.Run(new PasswordLockForm());  // 第3題 - 密碼鎖
            // Application.Run(new PasswordStrengthForm()); // 第4題 - 密碼強度
            // Application.Run(new DiceForm());          // 第5題 - 擲骰子
        }
    }
}
