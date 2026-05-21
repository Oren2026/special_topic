using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using WPF_POS.Models;

namespace WPF_POS.Services;

public class DataService
{
    private static readonly string DataFolder = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Data");
    private static readonly string DataFile = Path.Combine(DataFolder, "store.json");

    public List<Kind> Kinds { get; private set; } = [];
    public List<Tag> Tags { get; private set; } = [];
    public List<Product> Products { get; private set; } = [];

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true
    };

    public void Load()
    {
        if (!File.Exists(DataFile))
        {
            InitializeDefaultData();
            Save();
            return;
        }

        var json = File.ReadAllText(DataFile);
        var data = JsonSerializer.Deserialize<StoreData>(json, JsonOptions) ?? new StoreData();
        Kinds = data.Kinds;
        Tags = data.Tags;
        Products = data.Products;
    }

    public void Save()
    {
        Directory.CreateDirectory(DataFolder);
        var data = new StoreData { Kinds = Kinds, Tags = Tags, Products = Products };
        var json = JsonSerializer.Serialize(data, JsonOptions);
        File.WriteAllText(DataFile, json);
    }

    private void InitializeDefaultData()
    {
        Kinds = new List<Kind>
        {
            new() { Id = 1, Name = "漢堡", DisplayOrder = 1 },
            new() { Id = 2, Name = "副食", DisplayOrder = 2 },
            new() { Id = 3, Name = "飲料", DisplayOrder = 3 },
            new() { Id = 4, Name = "套餐", DisplayOrder = 4 }
        };

        Tags = new List<Tag>
        {
            new() { Id = 1, Name = "新品", Color = "#4CAF50" },
            new() { Id = 2, Name = "熱銷", Color = "#FF9800" },
            new() { Id = 3, Name = "限時", Color = "#F44336" }
        };

        Products = new List<Product>
        {
            new() { Id = 1, Name = "牛肉堡", Price = 70, KindId = 1, TagIds = new List<int> { 1 } },
            new() { Id = 2, Name = "雞腿堡", Price = 65, KindId = 1, TagIds = new List<int> { 2 } },
            new() { Id = 3, Name = "素食堡", Price = 60, KindId = 1, TagIds = new List<int>() },
            new() { Id = 4, Name = "薯條(大)", Price = 50, KindId = 2, TagIds = new List<int>() },
            new() { Id = 5, Name = "薯條(小)", Price = 35, KindId = 2, TagIds = new List<int>() },
            new() { Id = 6, Name = "雞塊", Price = 45, KindId = 2, TagIds = new List<int> { 2 } },
            new() { Id = 7, Name = "可樂", Price = 30, KindId = 3, TagIds = new List<int>() },
            new() { Id = 8, Name = "雪碧", Price = 30, KindId = 3, TagIds = new List<int>() },
            new() { Id = 9, Name = "奶茶", Price = 40, KindId = 3, TagIds = new List<int> { 1 } },
            new() { Id = 10, Name = "牛肉套餐", Price = 110, KindId = 4, TagIds = new List<int> { 2 } },
            new() { Id = 11, Name = "雞腿套餐", Price = 105, KindId = 4, TagIds = new List<int>() },
            new() { Id = 12, Name = "素食套餐", Price = 95, KindId = 4, TagIds = new List<int>() }
        };
    }

    // Kind CRUD
    public void AddKind(Kind kind) { Kinds.Add(kind); Save(); }
    public void UpdateKind(Kind kind) { var i = Kinds.FindIndex(k => k.Id == kind.Id); if (i >= 0) Kinds[i] = kind; Save(); }
    public void DeleteKind(int id) { Kinds.RemoveAll(k => k.Id == id); Save(); }

    // Tag CRUD
    public void AddTag(Tag tag) { Tags.Add(tag); Save(); }
    public void UpdateTag(Tag tag) { var i = Tags.FindIndex(t => t.Id == tag.Id); if (i >= 0) Tags[i] = tag; Save(); }
    public void DeleteTag(int id) { Tags.RemoveAll(t => t.Id == id); Save(); }

    // Product CRUD
    public void AddProduct(Product product) { Products.Add(product); Save(); }
    public void UpdateProduct(Product product) { var i = Products.FindIndex(p => p.Id == product.Id); if (i >= 0) Products[i] = product; Save(); }
    public void DeleteProduct(int id) { Products.RemoveAll(p => p.Id == id); Save(); }
}

public class StoreData
{
    public List<Kind> Kinds { get; set; } = new();
    public List<Tag> Tags { get; set; } = new();
    public List<Product> Products { get; set; } = new();
}