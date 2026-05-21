using System;
using System.Collections.Generic;
using System.Linq;

namespace WPF_POS.Models;

public class Order
{
    public List<OrderItem> Items { get; set; } = new List<OrderItem>();
    public decimal Subtotal => Items.Sum(x => x.Subtotal);
    public decimal Tax => Math.Round(Subtotal * 0.1m, 0);
    public decimal Total => Subtotal + Tax;
    public string PaymentMethod { get; set; } = "Cash";
    public decimal PaidAmount { get; set; }
    public decimal Change => PaidAmount - Total;
}