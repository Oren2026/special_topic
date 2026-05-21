using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using WPF_POS.Models;
using WPF_POS.Services;
using WPF_POS.ViewModels;
using WPF_POS.Views;

namespace WPF_POS;

public partial class MainWindow : Window
{
    private int _clickCount = 0;
    private System.Windows.Threading.DispatcherTimer? _clickTimer;
    private AdminViewModel? _adminVm;

    public MainWindow()
    {
        InitializeComponent();
        DataContext = App.MainViewModel;
        LoadFilters();
    }

    // ========== Load Filters ==========

    private void LoadFilters()
    {
        KindFilters.ItemsSource = App.DataService.Kinds.OrderBy(k => k.DisplayOrder).ToList();
        TagFilters.ItemsSource = App.DataService.Tags.ToList();
    }

    // ========== Kind / Tag Filter ==========

    private void KindFilter_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn)
        {
            var id = btn.Tag as int?;
            App.MainViewModel.SelectKind(id);
            UpdateKindButtonStyles();
        }
    }

    private void TagFilter_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn)
        {
            var id = btn.Tag as int?;
            App.MainViewModel.SelectTag(id);
            UpdateTagButtonStyles();
        }
    }

    private void UpdateKindButtonStyles()
    {
        if (KindFilters.Parent is Panel panel)
        {
            foreach (var child in panel.Children)
            {
                if (child is Button btn)
                {
                    var isSelected = btn.Tag == null && App.MainViewModel.SelectedKindId == null
                        || btn.Tag is int id && App.MainViewModel.SelectedKindId == id;
                    btn.Background = isSelected
                        ? (System.Windows.Media.Brush)FindResource("AccentBrush")
                        : (System.Windows.Media.Brush)FindResource("SecondaryBrush");
                }
            }
        }
    }

    private void UpdateTagButtonStyles()
    {
        // Tag button style update logic
    }

    // ========== Product Click ==========

    private void Product_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is Product product)
        {
            App.MainViewModel.AddToCartCommand.Execute(product);
            StatusText.Text = $"已加入：{product.Name}";
        }
    }

    // ========== Cart Operations ==========

    private void Increase_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is OrderItem item)
        {
            item.Quantity++;
            RefreshCart();
        }
    }

    private void Decrease_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is OrderItem item)
        {
            if (item.Quantity > 1) item.Quantity--;
            else App.MainViewModel.CartItems.Remove(item);
            RefreshCart();
        }
    }

    private void Remove_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button btn && btn.Tag is OrderItem item)
        {
            App.MainViewModel.CartItems.Remove(item);
            RefreshCart();
        }
    }

    private void RefreshCart()
    {
        App.MainViewModel.RefreshCart();
    }

    // ========== Checkout ==========

    private void Checkout_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new PaymentDialog(App.MainViewModel.CartTotal);
        dialog.Owner = this;
        if (dialog.ShowDialog() == true)
        {
            var order = new Order
            {
                PaymentMethod = dialog.PaymentMethod,
                PaidAmount = dialog.PaidAmount
            };
            foreach (var item in App.MainViewModel.CartItems.ToList())
            {
                order.Items.Add(item);
            }
            App.MainViewModel.CartItems.Clear();
            RefreshCart();
            StatusText.Text = $"交易完成！找零 ${order.Change:N0}";
        }
    }

    // ========== Cancel Transaction ==========

    private void CancelTransaction_Click(object sender, RoutedEventArgs e)
    {
        if (App.MainViewModel.CartItems.Count == 0) return;
        var result = MessageBox.Show("確定要取消當前交易？", "確認", MessageBoxButton.YesNo, MessageBoxImage.Warning);
        if (result == MessageBoxResult.Yes)
        {
            App.MainViewModel.CartItems.Clear();
            RefreshCart();
            StatusText.Text = "交易已取消";
        }
    }

    // ========== 5-Click to Admin ==========

    private void Title_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        _clickTimer?.Stop();
        _clickTimer = new System.Windows.Threading.DispatcherTimer { Interval = TimeSpan.FromMilliseconds(400) };
        _clickTimer.Tick += (s, ev) =>
        {
            _clickCount = 0;
            _clickTimer!.Stop();
        };
        _clickTimer.Start();

        _clickCount++;
        if (_clickCount >= 5)
        {
            _clickTimer.Stop();
            _clickCount = 0;
            ShowAdminView();
        }
    }

    // ========== Admin View ==========

    private void ShowAdminView()
    {
        POSView.Visibility = Visibility.Collapsed;
        AdminView.Visibility = Visibility.Visible;
        _adminVm ??= new AdminViewModel(App.DataService);
        ShowProductManagement_Click(null!, null!);
    }

    private void BackToPOS_Click(object sender, RoutedEventArgs e)
    {
        AdminView.Visibility = Visibility.Collapsed;
        POSView.Visibility = Visibility.Visible;
    }

    private void ShowProductManagement_Click(object sender, RoutedEventArgs e)
    {
        if (_adminVm != null)
            AdminContent.Children.Clear();
            AdminContent.Children.Add(new ProductManagementControl(_adminVm));
    }

    private void ShowKindManagement_Click(object sender, RoutedEventArgs e)
    {
        if (_adminVm != null)
            AdminContent.Children.Clear();
            AdminContent.Children.Add(new KindManagementControl(_adminVm));
    }

    private void ShowTagManagement_Click(object sender, RoutedEventArgs e)
    {
        if (_adminVm != null)
            AdminContent.Children.Clear();
            AdminContent.Children.Add(new TagManagementControl(_adminVm));
    }
}