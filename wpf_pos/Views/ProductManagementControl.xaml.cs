using System.Windows;
using System.Windows.Controls;
using WPF_POS.Models;
using WPF_POS.ViewModels;

namespace WPF_POS.Views;

public partial class ProductManagementControl : UserControl
{
    private readonly AdminViewModel _vm;
    private Product? _editingProduct;

    public ProductManagementControl(AdminViewModel vm)
    {
        InitializeComponent();
        _vm = vm;
        DataContext = _vm;
        _vm.LoadKinds();
        _vm.LoadTags();
    }

    private void AddProduct_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new ProductEditDialog(_vm.Kinds, _vm.Tags);
        dialog.Owner = Window.GetWindow(this);
        if (dialog.ShowDialog() == true)
        {
            _vm.AddProduct(dialog.ProductName, dialog.ProductPrice, dialog.SelectedKindId, dialog.SelectedTagIds);
        }
    }

    private void EditProduct_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is Product product)
        {
            var dialog = new ProductEditDialog(_vm.Kinds, _vm.Tags, product);
            dialog.Owner = Window.GetWindow(this);
            if (dialog.ShowDialog() == true)
            {
                product.Name = dialog.ProductName;
                product.Price = dialog.ProductPrice;
                product.KindId = dialog.SelectedKindId;
                product.TagIds = dialog.SelectedTagIds;
                _vm.UpdateProduct(product);
            }
        }
    }

    private void DeleteProduct_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is Product product)
        {
            var result = MessageBox.Show($"確定刪除「{product.Name}」？", "確認", MessageBoxButton.YesNo, MessageBoxImage.Warning);
            if (result == MessageBoxResult.Yes)
                _vm.DeleteProduct(product.Id);
        }
    }
}