using System.Windows;
using System.Windows.Controls;

namespace WPF_POS.Views;

public partial class PaymentDialog : Window
{
    private readonly decimal _total;

    public string PaymentMethod { get; private set; } = "Cash";
    public decimal PaidAmount { get; private set; }
    public decimal Change => PaidAmount - _total;

    public PaymentDialog(decimal total)
    {
        InitializeComponent();
        _total = total;
        TotalText.Text = total.ToString("N0");
    }

    private void PaymentMethod_Changed(object sender, RoutedEventArgs e)
    {
        if (CashPanel != null)
        {
            var isCash = CashRadio.IsChecked == true;
            CashPanel.Visibility = isCash ? Visibility.Visible : Visibility.Collapsed;
            ChangePanel.Visibility = isCash ? Visibility.Visible : Visibility.Collapsed;

            if (isCash && !string.IsNullOrEmpty(PaidBox.Text))
                UpdateChange();
        }
    }

    private void PaidBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        UpdateChange();
    }

    private void UpdateChange()
    {
        if (decimal.TryParse(PaidBox.Text, out var paid))
        {
            PaidAmount = paid;
            var change = paid - _total;
            ChangeText.Text = $"${change:N0}";
            ConfirmBtn.IsEnabled = change >= 0;
        }
    }

    private void Confirm_Click(object sender, RoutedEventArgs e)
    {
        PaymentMethod = CashRadio.IsChecked == true ? "Cash" : "Card";

        if (PaymentMethod == "Cash")
        {
            if (!decimal.TryParse(PaidBox.Text, out var paid))
            {
                MessageBox.Show("請輸入有效金額", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            if (paid < _total)
            {
                MessageBox.Show("金額不足", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }
            PaidAmount = paid;
        }
        else
        {
            PaidAmount = _total;
        }

        DialogResult = true;
    }

    private void Cancel_Click(object sender, RoutedEventArgs e) => Close();
}