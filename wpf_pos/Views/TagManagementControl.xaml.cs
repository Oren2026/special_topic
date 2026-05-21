using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using WPF_POS.Models;
using WPF_POS.ViewModels;

namespace WPF_POS.Views;

public partial class TagManagementControl : UserControl
{
    private readonly AdminViewModel _vm;

    public TagManagementControl(AdminViewModel vm)
    {
        InitializeComponent();
        _vm = vm;
        DataContext = _vm;
        _vm.LoadTags();
    }

    private void AddTag_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new TagEditDialog("新增標籤");
        dialog.Owner = Window.GetWindow(this);
        if (dialog.ShowDialog() == true)
            _vm.AddTag(dialog.TagName, dialog.TagColor);
    }

    private void EditTag_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is Tag tag)
        {
            var dialog = new TagEditDialog("編輯標籤", tag.Name, tag.Color);
            dialog.Owner = Window.GetWindow(this);
            if (dialog.ShowDialog() == true)
            {
                tag.Name = dialog.TagName;
                tag.Color = dialog.TagColor;
                _vm.UpdateTag(tag);
            }
        }
    }

    private void DeleteTag_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is Tag tag)
        {
            var result = MessageBox.Show($"確定刪除「{tag.Name}」？", "確認", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (result == MessageBoxResult.Yes)
                _vm.DeleteTag(tag.Id);
        }
    }
}