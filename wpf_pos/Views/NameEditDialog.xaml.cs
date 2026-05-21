using System.Windows;

namespace WPF_POS.Views;

public partial class NameEditDialog : Window
{
    public string InputText { get; private set; } = "";

    public NameEditDialog(string title, string label, string defaultValue = "")
    {
        InitializeComponent();
        DialogTitle.Text = title;
        LabelText.Text = label;
        InputBox.Text = defaultValue;
    }

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(InputBox.Text))
        {
            MessageBox.Show("請輸入內容", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        InputText = InputBox.Text.Trim();
        DialogResult = true;
    }

    private void Cancel_Click(object sender, RoutedEventArgs e) => Close();
}