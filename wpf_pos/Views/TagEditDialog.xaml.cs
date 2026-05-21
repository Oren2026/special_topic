using System.Windows;

namespace WPF_POS.Views;

public partial class TagEditDialog : Window
{
    public string TagName { get; private set; } = "";
    public string TagColor { get; private set; } = "#4CAF50";

    public TagEditDialog(string title, string defaultName = "", string defaultColor = "#4CAF50")
    {
        InitializeComponent();
        DialogTitle.Text = title;
        NameBox.Text = defaultName;
        ColorBox.Text = defaultColor;
    }

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(NameBox.Text))
        {
            MessageBox.Show("請輸入標籤名稱", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        TagName = NameBox.Text.Trim();
        TagColor = ColorBox.Text.Trim();
        if (!TagColor.StartsWith("#")) TagColor = "#" + TagColor;

        DialogResult = true;
    }

    private void Cancel_Click(object sender, RoutedEventArgs e) => Close();
}