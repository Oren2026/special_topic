using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using WPF_POS.Models;
using WPF_POS.Services;

namespace WPF_POS.ViewModels;

public class MainViewModel : INotifyPropertyChanged
{
    private readonly DataService _data;

    public MainViewModel(DataService data)
    {
        _data = data;
        _data.Load();

        // 種類：全部種類都載入（不是只取第一個商品的）
        foreach (var k in _data.Kinds.OrderBy(k => k.DisplayOrder))
            Kinds.Add(k);

        // 標籤：全部標籤都載入
        foreach (var t in _data.Tags)
            Tags.Add(t);

        UpdateFilteredProducts();
    }

    // ========== Properties ==========

    public ObservableCollection<Kind> Kinds { get; } = new ObservableCollection<Kind>();
    public ObservableCollection<Tag> Tags { get; } = new ObservableCollection<Tag>();
    public ObservableCollection<Product> FilteredProducts { get; } = new ObservableCollection<Product>();
    public ObservableCollection<OrderItem> CartItems { get; } = new ObservableCollection<OrderItem>();

    private int? _selectedKindId;
    public int? SelectedKindId
    {
        get => _selectedKindId;
        set
        {
            if (_selectedKindId != value)
            {
                _selectedKindId = value;
                OnPropertyChanged();
                UpdateFilteredProducts();
            }
        }
    }

    private int? _selectedTagId;
    public int? SelectedTagId
    {
        get => _selectedTagId;
        set
        {
            if (_selectedTagId != value)
            {
                _selectedTagId = value;
                OnPropertyChanged();
                UpdateFilteredProducts();
            }
        }
    }

    public decimal CartSubtotal => CartItems.Sum(x => x.Subtotal);
    public decimal CartTax => Math.Round(CartSubtotal * 0.1m, 0);
    public decimal CartTotal => CartSubtotal + CartTax;

    // ========== Commands ==========

    public ICommand AddToCartCommand => new RelayCommand<Product>(p => AddToCart(p));
    public ICommand IncreaseCommand => new RelayCommand<OrderItem>(i => { i.Quantity++; RefreshCartTotals(); });
    public ICommand DecreaseCommand => new RelayCommand<OrderItem>(i => { if (i.Quantity > 1) i.Quantity--; else CartItems.Remove(i); RefreshCartTotals(); });
    public ICommand RemoveFromCartCommand => new RelayCommand<OrderItem>(i => { CartItems.Remove(i); RefreshCartTotals(); });
    public ICommand ClearCartCommand => new RelayCommand(() => { CartItems.Clear(); RefreshCartTotals(); });
    public ICommand CheckoutCommand => new RelayCommand(() => { }, () => CartItems.Count > 0);

    // ========== Methods ==========

    private void AddToCart(Product product)
    {
        var existing = CartItems.FirstOrDefault(x => x.Product.Id == product.Id);
        if (existing != null) existing.Quantity++;
        else CartItems.Add(new OrderItem { Product = product, Quantity = 1 });
        RefreshCartTotals();
    }

    internal void RefreshCart()
    {
        RefreshCartTotals();
    }

    private void RefreshCartTotals()
    {
        OnPropertyChanged(nameof(CartSubtotal));
        OnPropertyChanged(nameof(CartTax));
        OnPropertyChanged(nameof(CartTotal));
        OnPropertyChanged(nameof(CartItems));
    }

    private void UpdateFilteredProducts()
    {
        FilteredProducts.Clear();
        var filtered = _data.Products.AsEnumerable();

        if (_selectedKindId.HasValue)
            filtered = filtered.Where(p => p.KindId == _selectedKindId.Value);

        if (_selectedTagId.HasValue)
            filtered = filtered.Where(p => p.TagIds.Contains(_selectedTagId.Value));

        foreach (var p in filtered)
            FilteredProducts.Add(p);
    }

    public string GetKindName(int kindId) => _data.Kinds.FirstOrDefault(k => k.Id == kindId)?.Name ?? "";
    public List<Tag> GetProductTags(Product p) => _data.Tags.Where(t => p.TagIds.Contains(t.Id)).ToList();

    public void SelectKind(int? id)
    {
        SelectedKindId = _selectedKindId == id ? null : id;
    }

    public void SelectTag(int? id)
    {
        SelectedTagId = _selectedTagId == id ? null : id;
    }

    // ========== INotifyPropertyChanged ==========

    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public class RelayCommand : ICommand
{
    private readonly Action _execute;
    private readonly Func<bool>? _canExecute;

    public RelayCommand(Action execute, Func<bool>? canExecute = null)
    {
        _execute = execute;
        _canExecute = canExecute;
    }

#pragma warning disable CS0067
    public event EventHandler? CanExecuteChanged
    {
        add => CommandManager.RequerySuggested += value;
        remove => CommandManager.RequerySuggested -= value;
    }
#pragma warning restore CS0067

    public bool CanExecute(object? parameter) => _canExecute?.Invoke() ?? true;
    public void Execute(object? parameter) => _execute();
}

public class RelayCommand<T> : ICommand
{
    private readonly Action<T?> _execute;
    private readonly Func<bool>? _canExecute;

    public RelayCommand(Action<T?> execute, Func<bool>? canExecute = null)
    {
        _execute = execute;
        _canExecute = canExecute;
    }

#pragma warning disable CS0067
    public event EventHandler? CanExecuteChanged
    {
        add => CommandManager.RequerySuggested += value;
        remove => CommandManager.RequerySuggested -= value;
    }
#pragma warning restore CS0067

    public bool CanExecute(object? parameter) => _canExecute?.Invoke() ?? true;
    public void Execute(object? parameter) => _execute(parameter != null ? (T)parameter : default);
}