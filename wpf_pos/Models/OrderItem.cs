using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace WPF_POS.Models;

public class OrderItem : INotifyPropertyChanged
{
    private int _quantity = 1;
    public Product Product { get; set; } = new Product();

    public int Quantity
    {
        get => _quantity;
        set
        {
            if (_quantity != value)
            {
                _quantity = value;
                OnPropertyChanged();
                OnPropertyChanged(nameof(Subtotal));
            }
        }
    }

    public decimal Subtotal => Product.Price * Quantity;

    public event PropertyChangedEventHandler? PropertyChanged;
    protected void OnPropertyChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}