using System.Windows;
using WPF_POS.Services;
using WPF_POS.ViewModels;

namespace WPF_POS;

public partial class App : Application
{
    public static DataService DataService { get; private set; } = null!;
    public static MainViewModel MainViewModel { get; private set; } = null!;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        DataService = new DataService();
        MainViewModel = new MainViewModel(DataService);
    }
}