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
        Kinds = new ObservableCollection<Kind>(_data.Kinds.Where(k => k.Id == _data.Products.First().KindId));
        UpdateFilteredProducts();
    }

    // ========== Properties ==========

    public ObservableCollection<Kind> Kinds { get; } = new();
    public ObservableCollection<Tag> Tags { get; } = new();
    public ObservableCollection<Product> FilteredProducts { get; } = new();
    public ObservableCollection<OrderItem> CartItems { get; } = new();
    public ObservableCollection<Product> AllProducts => new(_data.Products);

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
    public ICommand IncreaseCommand => new RelayCommand<OrderItem>(i => { i.Quantity++; OnPropertyChanged(nameof(CartItems)); RefreshCart(); });
    public ICommand DecreaseCommand => new RelayCommand<OrderItem>(i => { if (i.Quantity > 1) i.Quantity--; else CartItems.Remove(i); RefreshCart(); });
    public ICommand RemoveFromCartCommand => new RelayCommand<OrderItem>(i => { CartItems.Remove(i); RefreshCart(); });
    public ICommand ClearCartCommand => new RelayCommand(() => { CartItems.Clear(); RefreshCart(); });
    public ICommand CheckoutCommand => new RelayCommand(() => { }, () => CartItems.Count > 0);

    // ========== Methods ==========

    private void AddToCart(Product product)
    {
        var existing = CartItems.FirstOrDefault(x => x.Product.Id == product.Id);
        if (existing != null) existing.Quantity++;
        else CartItems.Add(new OrderItem { Product = product, Quantity = 1 });
        RefreshCart();
    }

    internal void RefreshCart()
    {
        OnPropertyChanged(nameof(CartSubtotal));
        OnPropertyChanged(nameof(CartTax));
        OnPropertyChanged(nameof(CartTotal));
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
        SelectedKindId = id == SelectedKindId ? null : id;
    }

    public void SelectTag(int? id)
    {
        SelectedTagId = id == SelectedTagId ? null : id;
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
    public void Execute(object? parameter) => _execute(parameter);
}