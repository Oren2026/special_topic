using System.Windows;
using System.Windows.Controls;
using WPF_POS.Models;
using WPF_POS.ViewModels;

namespace WPF_POS.Views;

public partial class KindManagementControl : UserControl
{
    private readonly AdminViewModel _vm;

    public KindManagementControl(AdminViewModel vm)
    {
        InitializeComponent();
        _vm = vm;
        DataContext = _vm;
        _vm.LoadKinds();
    }

    private void AddKind_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new NameEditDialog("新增種類", "種類名稱");
        dialog.Owner = Window.GetWindow(this);
        if (dialog.ShowDialog() == true)
            _vm.AddKind(dialog.InputText);
    }

    private void EditKind_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is Kind kind)
        {
            var dialog = new NameEditDialog("編輯種類", "種類名稱", kind.Name);
            dialog.Owner = Window.GetWindow(this);
            if (dialog.ShowDialog() == true)
            {
                kind.Name = dialog.InputText;
                _vm.UpdateKind(kind);
            }
        }
    }

    private void DeleteKind_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is Kind kind)
        {
            var result = MessageBox.Show($"確定刪除「{kind.Name}」？\n注意：此種類下的商品不會被刪除，但會變成「無種類」。", "確認", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (result == MessageBoxResult.Yes)
                _vm.DeleteKind(kind.Id);
        }
    }
}