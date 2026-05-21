namespace WPF_POS.Models;

public class OrderItem
{
    public Product Product { get; set; } = new();
    public int Quantity { get; set; } = 1;
    public decimal Subtotal => Product.Price * Quantity;
}