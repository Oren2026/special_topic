using System.Collections.ObjectModel;
using System.Windows;
using WPF_POS.Models;

namespace WPF_POS.Views;

public partial class ProductEditDialog : Window
{
    public string ProductName { get; private set; } = "";
    public decimal ProductPrice { get; private set; }
    public int SelectedKindId { get; private set; }
    public List<int> SelectedTagIds { get; private set; } = [];

    public ProductEditDialog(ObservableCollection<Kind> kinds, ObservableCollection<Tag> tags, Product? editProduct = null)
    {
        InitializeComponent();

        KindCombo.ItemsSource = kinds;
        TagList.ItemsSource = tags;

        if (editProduct != null)
        {
            DialogTitle.Text = "編輯商品";
            NameBox.Text = editProduct.Name;
            PriceBox.Text = editProduct.Price.ToString();
            SelectedKindId = editProduct.KindId;
            SelectedTagIds = editProduct.TagIds;

            // 選中種類
            for (int i = 0; i < kinds.Count; i++)
            {
                if (kinds[i].Id == editProduct.KindId)
                {
                    KindCombo.SelectedIndex = i;
                    break;
                }
            }

            // 選中標籤
            foreach (var item in TagList.Items)
            {
                if (item is Tag tag && editProduct.TagIds.Contains(tag.Id))
                {
                    TagList.SelectedItems.Add(item);
                }
            }
        }
        else
        {
            DialogTitle.Text = "新增商品";
            if (kinds.Count > 0) KindCombo.SelectedIndex = 0;
        }
    }

    private void Save_Click(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(NameBox.Text))
        {
            MessageBox.Show("請輸入商品名稱", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        if (!decimal.TryParse(PriceBox.Text, out var price) || price < 0)
        {
            MessageBox.Show("請輸入有效價格", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        ProductName = NameBox.Text.Trim();
        ProductPrice = price;
        SelectedKindId = (KindCombo.SelectedItem as Kind)?.Id ?? 0;

        SelectedTagIds.Clear();
        foreach (Tag tag in TagList.SelectedItems)
            SelectedTagIds.Add(tag.Id);

        DialogResult = true;
    }

    private void Cancel_Click(object sender, RoutedEventArgs e) => Close();
}