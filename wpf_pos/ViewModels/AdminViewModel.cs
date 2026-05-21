using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using WPF_POS.Models;
using WPF_POS.Services;

namespace WPF_POS.ViewModels;

public class AdminViewModel : INotifyPropertyChanged
{
    private readonly DataService _data;

    public AdminViewModel(DataService data)
    {
        _data = data;
        Products = [_data.Products];
        Kinds = [_data.Kinds];
        Tags = [_data.Tags];
    }

    // ========== Products ==========

    public ObservableCollection<Product> Products { get; }
    public ObservableCollection<Kind> Kinds { get; }
    public ObservableCollection<Tag> Tags { get; }

    private Product? _selectedProduct;
    public Product? SelectedProduct
    {
        get => _selectedProduct;
        set { _selectedProduct = value; OnPropertyChanged(); }
    }

    private string _productSearchText = "";
    public string ProductSearchText
    {
        get => _productSearchText;
        set
        {
            _productSearchText = value;
            OnPropertyChanged();
            FilterProducts();
        }
    }

    public ObservableCollection<Product> FilteredProducts { get; } = [];

    private void FilterProducts()
    {
        FilteredProducts.Clear();
        var filtered = _data.Products.AsEnumerable();
        if (!string.IsNullOrWhiteSpace(_productSearchText))
            filtered = filtered.Where(p => p.Name.Contains(_productSearchText, StringComparison.OrdinalIgnoreCase));
        foreach (var p in filtered) FilteredProducts.Add(p);
    }

    public void AddProduct(string name, decimal price, int kindId, List<int> tagIds)
    {
        var id = _data.Products.Count > 0 ? _data.Products.Max(p => p.Id) + 1 : 1;
        var product = new Product { Id = id, Name = name, Price = price, KindId = kindId, TagIds = tagIds };
        _data.AddProduct(product);
        Products.Add(product);
        FilteredProducts.Add(product);
    }

    public void UpdateProduct(Product product)
    {
        _data.UpdateProduct(product);
        var i = Products.FirstIndex(p => p.Id == product.Id);
        if (i >= 0) Products[i] = product;
        var j = FilteredProducts.FirstIndex(p => p.Id == product.Id);
        if (j >= 0) FilteredProducts[j] = product;
    }

    public void DeleteProduct(int id)
    {
        _data.DeleteProduct(id);
        Products.RemoveAll(p => p.Id == id);
        FilteredProducts.RemoveAll(p => p.Id == id);
    }

    // ========== Kinds ==========

    private Kind? _selectedKind;
    public Kind? SelectedKind
    {
        get => _selectedKind;
        set { _selectedKind = value; OnPropertyChanged(); }
    }

    public ObservableCollection<Kind> FilteredKinds { get; } = [];

    public void LoadKinds()
    {
        FilteredKinds.Clear();
        foreach (var k in _data.Kinds.OrderBy(k => k.DisplayOrder)) FilteredKinds.Add(k);
    }

    public void AddKind(string name)
    {
        var id = _data.Kinds.Count > 0 ? _data.Kinds.Max(k => k.Id) + 1 : 1;
        var maxOrder = _data.Kinds.Count > 0 ? _data.Kinds.Max(k => k.DisplayOrder) : 0;
        var kind = new Kind { Id = id, Name = name, DisplayOrder = maxOrder + 1 };
        _data.AddKind(kind);
        Kinds.Add(kind);
        FilteredKinds.Add(kind);
    }

    public void UpdateKind(Kind kind)
    {
        _data.UpdateKind(kind);
        var i = Kinds.FirstIndex(k => k.Id == kind.Id);
        if (i >= 0) Kinds[i] = kind;
        var j = FilteredKinds.FirstIndex(k => k.Id == kind.Id);
        if (j >= 0) FilteredKinds[j] = kind;
    }

    public void DeleteKind(int id)
    {
        _data.DeleteKind(id);
        Kinds.RemoveAll(k => k.Id == id);
        FilteredKinds.RemoveAll(k => k.Id == id);
    }

    // ========== Tags ==========

    private Tag? _selectedTag;
    public Tag? SelectedTag
    {
        get => _selectedTag;
        set { _selectedTag = value; OnPropertyChanged(); }
    }

    public ObservableCollection<Tag> FilteredTags { get; } = [];

    public void LoadTags()
    {
        FilteredTags.Clear();
        foreach (var t in _data.Tags) FilteredTags.Add(t);
    }

    public void AddTag(string name, string color)
    {
        var id = _data.Tags.Count > 0 ? _data.Tags.Max(t => t.Id) + 1 : 1;
        var tag = new Tag { Id = id, Name = name, Color = color };
        _data.AddTag(tag);
        Tags.Add(tag);
        FilteredTags.Add(tag);
    }

    public void UpdateTag(Tag tag)
    {
        _data.UpdateTag(tag);
        var i = Tags.FirstIndex(t => t.Id == tag.Id);
        if (i >= 0) Tags[i] = tag;
        var j = FilteredTags.FirstIndex(t => t.Id == tag.Id);
        if (j >= 0) FilteredTags[j] = tag;
    }

    public void DeleteTag(int id)
    {
        _data.DeleteTag(id);
        Tags.RemoveAll(t => t.Id == id);
        FilteredTags.RemoveAll(t => t.Id == id);
    }

    // ========== Helpers ==========

    public string GetKindName(int kindId) => _data.Kinds.FirstOrDefault(k => k.Id == kindId)?.Name ?? "";
    public List<Tag> GetProductTags(Product p) => _data.Tags.Where(t => p.TagIds.Contains(t.Id)).ToList();

    // ========== INotifyPropertyChanged ==========

    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public static class ObservableCollectionExtensions
{
    public static int FirstIndex<T>(this ObservableCollection<T> collection, Func<T, bool> predicate)
    {
        for (int i = 0; i < collection.Count; i++)
            if (predicate(collection[i])) return i;
        return -1;
    }
}