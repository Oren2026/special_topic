using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Media;
using System.Windows.Forms;
using System.Text.Json;

namespace timeclock
{
    public partial class Form1 : Form
    {
        // ==================== 鬧鐘資料結構 ====================
        private class AlarmItem
        {
            public DateTime Time { get; set; }
            public bool Enabled { get; set; }
            public string Display => Time.ToString("HH:mm");
        }

        // ==================== UI 控制項 ====================
        private Label lblCurrentTime;
        private Label lblCurrentDate;
        private ListView lvAlarms;
        private DateTimePicker dtpTime;
        private Button btnAdd;
        private Button btnDelete;
        private Button btnToggle;
        private Label lblStatus;
        private System.Windows.Forms.Timer timerClock;
        private System.Windows.Forms.Timer timerCheck;

        // ==================== 資料 ====================
        private List<AlarmItem> alarms = new List<AlarmItem>();
        private string alarmFilePath;
        private const string ALARM_FILE = "alarms.json";

        // ==================== 建構子 ====================
        public Form1()
        {
            InitializeComponent();
            InitControls();
            LoadAlarms();
        }

        // ==================== 初始化 UI ====================
        private void InitControls()
        {
            // ---------- Form 基本設定 ----------
            this.Text = "⏰ 小鬧鐘";
            this.ClientSize = new Size(680, 420);
            this.FormBorderStyle = FormBorderStyle.FixedSingle;
            this.MaximizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(255, 250, 240);

            // ---------- 左欄：時鐘區 ----------
            lblCurrentTime = new Label();
            lblCurrentTime.Text = DateTime.Now.ToString("HH:mm:ss");
            lblCurrentTime.Location = new Point(20, 20);
            lblCurrentTime.Size = new Size(260, 80);
            lblCurrentTime.Font = new Font("Segoe UI", 42F, FontStyle.Bold);
            lblCurrentTime.ForeColor = Color.FromArgb(33, 33, 33);
            lblCurrentTime.TextAlign = ContentAlignment.MiddleCenter;
            lblCurrentTime.BackColor = Color.FromArgb(255, 250, 240);
            this.Controls.Add(lblCurrentTime);

            lblCurrentDate = new Label();
            lblCurrentDate.Text = DateTime.Now.ToString("yyyy 年 MM 月 dd 日  dddd");
            lblCurrentDate.Location = new Point(20, 105);
            lblCurrentDate.Size = new Size(260, 25);
            lblCurrentDate.Font = new Font("Microsoft JhengHei UI", 10F);
            lblCurrentDate.ForeColor = Color.FromArgb(97, 97, 97);
            lblCurrentDate.TextAlign = ContentAlignment.MiddleCenter;
            this.Controls.Add(lblCurrentDate);

            // ---------- 時鐘 Timer ----------
            timerClock = new System.Windows.Forms.Timer();
            timerClock.Interval = 1000;
            timerClock.Tick += (s, e) =>
            {
                lblCurrentTime.Text = DateTime.Now.ToString("HH:mm:ss");
                lblCurrentDate.Text = DateTime.Now.ToString("yyyy 年 MM 月 dd 日  dddd");
            };
            timerClock.Start();

            // ---------- 左欄：設定區 ----------
            dtpTime = new DateTimePicker();
            dtpTime.Location = new Point(20, 160);
            dtpTime.Size = new Size(180, 30);
            dtpTime.Format = DateTimePickerFormat.Time;
            dtpTime.ShowUpDown = true;
            dtpTime.Font = new Font("Microsoft JhengHei UI", 11F);
            this.Controls.Add(dtpTime);

            btnAdd = new Button();
            btnAdd.Text = "新增鬧鐘";
            btnAdd.Location = new Point(210, 158);
            btnAdd.Size = new Size(100, 34);
            btnAdd.BackColor = Color.FromArgb(76, 175, 80);
            btnAdd.ForeColor = Color.White;
            btnAdd.FlatStyle = FlatStyle.Flat;
            btnAdd.Font = new Font("Microsoft JhengHei UI", 10F, FontStyle.Bold);
            btnAdd.FlatAppearance.BorderSize = 0;
            btnAdd.Click += BtnAdd_Click;
            this.Controls.Add(btnAdd);

            btnDelete = new Button();
            btnDelete.Text = "刪除選取";
            btnDelete.Location = new Point(20, 205);
            btnDelete.Size = new Size(100, 34);
            btnDelete.BackColor = Color.FromArgb(244, 67, 54);
            btnDelete.ForeColor = Color.White;
            btnDelete.FlatStyle = FlatStyle.Flat;
            btnDelete.Font = new Font("Microsoft JhengHei UI", 10F, FontStyle.Bold);
            btnDelete.FlatAppearance.BorderSize = 0;
            btnDelete.Enabled = false;
            btnDelete.Click += BtnDelete_Click;
            this.Controls.Add(btnDelete);

            btnToggle = new Button();
            btnToggle.Text = "啟用/停用";
            btnToggle.Location = new Point(130, 205);
            btnToggle.Size = new Size(100, 34);
            btnToggle.BackColor = Color.FromArgb(255, 152, 0);
            btnToggle.ForeColor = Color.White;
            btnToggle.FlatStyle = FlatStyle.Flat;
            btnToggle.Font = new Font("Microsoft JhengHei UI", 10F, FontStyle.Bold);
            btnToggle.FlatAppearance.BorderSize = 0;
            btnToggle.Enabled = false;
            btnToggle.Click += BtnToggle_Click;
            this.Controls.Add(btnToggle);

            lblStatus = new Label();
            lblStatus.Text = "共 0 個鬧鐘";
            lblStatus.Location = new Point(20, 250);
            lblStatus.Size = new Size(260, 20);
            lblStatus.Font = new Font("Microsoft JhengHei UI", 9F);
            lblStatus.ForeColor = Color.FromArgb(97, 97, 97);
            lblStatus.TextAlign = ContentAlignment.MiddleCenter;
            this.Controls.Add(lblStatus);

            // ---------- 右欄：鬧鐘清單 ----------
            lvAlarms = new ListView();
            lvAlarms.Location = new Point(340, 20);
            lvAlarms.Size = new Size(320, 370);
            lvAlarms.View = View.Details;
            lvAlarms.FullRowSelect = true;
            lvAlarms.GridLines = true;
            lvAlarms.Font = new Font("Microsoft JhengHei UI", 11F);
            lvAlarms.BackColor = Color.White;
            lvAlarms.Columns.Add("時間", 80);
            lvAlarms.Columns.Add("狀態", 70);
            lvAlarms.Columns.Add("下次響鈴", 150);
            lvAlarms.SelectedIndexChanged += LvAlarms_SelectedIndexChanged;
            this.Controls.Add(lvAlarms);

            // ---------- 鬧鐘檢查 Timer ----------
            timerCheck = new System.Windows.Forms.Timer();
            timerCheck.Interval = 1000;
            timerCheck.Tick += TimerCheck_Tick;
            timerCheck.Start();
        }

        // ==================== 新增鬧鐘 ====================
        private void BtnAdd_Click(object? sender, EventArgs e)
        {
            DateTime selectedTime = dtpTime.Value;
            DateTime alarmTime = DateTime.Today.Add(selectedTime.TimeOfDay);

            if (alarmTime <= DateTime.Now)
                alarmTime = alarmTime.AddDays(1);

            alarms.Add(new AlarmItem { Time = alarmTime, Enabled = true });
            SaveAlarms();
            RefreshListView();
        }

        // ==================== 刪除選取 ====================
        private void BtnDelete_Click(object? sender, EventArgs e)
        {
            if (lvAlarms.SelectedIndices.Count == 0) return;
            alarms.RemoveAt(lvAlarms.SelectedIndices[0]);
            SaveAlarms();
            RefreshListView();
        }

        // ==================== 啟用/停用 ====================
        private void BtnToggle_Click(object? sender, EventArgs e)
        {
            if (lvAlarms.SelectedIndices.Count == 0) return;
            int index = lvAlarms.SelectedIndices[0];
            alarms[index].Enabled = !alarms[index].Enabled;
            SaveAlarms();
            RefreshListView();
        }

        // ==================== 選取變化 ====================
        private void LvAlarms_SelectedIndexChanged(object? sender, EventArgs e)
        {
            bool hasSelection = lvAlarms.SelectedIndices.Count > 0;
            btnDelete.Enabled = hasSelection;
            btnToggle.Enabled = hasSelection;
        }

        // ==================== 每秒檢查鬧鐘 ====================
        private void TimerCheck_Tick(object? sender, EventArgs e)
        {
            DateTime now = DateTime.Now;

            foreach (AlarmItem alarm in alarms)
            {
                if (!alarm.Enabled) continue;

                if (alarm.Time.Hour == now.Hour &&
                    alarm.Time.Minute == now.Minute &&
                    now.Second == 0)
                {
                    TriggerAlarm(alarm);
                    break;
                }
            }

            UpdateNextAlarmStatus();
        }

        // ==================== 觸發鬧鐘 ====================
        private void TriggerAlarm(AlarmItem alarm)
        {
            try { SystemSounds.Exclamation.Play(); } catch { }

            string msg = "⏰ 鬧鐘响了！\n\n時間：" + alarm.Time.ToString("HH:mm");
            MessageBox.Show(msg, "鬧鐘", MessageBoxButtons.OK, MessageBoxIcon.Information);

            if (alarm.Time <= DateTime.Now)
            {
                alarm.Time = alarm.Time.AddDays(1);
                SaveAlarms();
                RefreshListView();
            }
        }

        // ==================== 更新狀態列 ====================
        private void UpdateNextAlarmStatus()
        {
            int count = alarms.Count;
            if (count == 0) { lblStatus.Text = "共 0 個鬧鐘"; return; }

            AlarmItem? next = null;
            foreach (AlarmItem a in alarms)
            {
                if (!a.Enabled) continue;
                if (next == null || a.Time < next.Time) next = a;
            }

            if (next != null)
            {
                TimeSpan diff = next.Time - DateTime.Now;
                if (diff.TotalSeconds < 0) diff = diff.Add(TimeSpan.FromDays(1));

                string timeStr = next.Time.ToString("HH:mm");
                string remainStr = diff.TotalHours >= 1
                    ? "約 " + (int)diff.TotalHours + " 小時後"
                    : "約 " + (int)diff.TotalMinutes + " 分鐘後";

                lblStatus.Text = "下次：" + timeStr + "｜" + remainStr;
            }
            else
            {
                lblStatus.Text = "共 " + count + " 個（全部停用）";
            }
        }

        // ==================== 刷新 ListView ====================
        private void RefreshListView()
        {
            lvAlarms.Items.Clear();

            foreach (AlarmItem alarm in alarms)
            {
                string status = alarm.Enabled ? "🔔 啟用" : "🔕 停用";

                DateTime nextRing = alarm.Time;
                if (nextRing <= DateTime.Now) nextRing = nextRing.AddDays(1);

                ListViewItem item = new ListViewItem(alarm.Display);
                item.SubItems.Add(status);
                item.SubItems.Add(nextRing.ToString("yyyy/MM/dd HH:mm"));
                if (!alarm.Enabled) item.ForeColor = Color.Gray;

                lvAlarms.Items.Add(item);
            }

            UpdateNextAlarmStatus();
        }

        // ==================== JSON 儲存 ====================
        private void SaveAlarms()
        {
            try
            {
                alarmFilePath = Path.Combine(Application.StartupPath, ALARM_FILE);
                string json = JsonSerializer.Serialize(alarms, new JsonSerializerOptions { WriteIndented = true });
                File.WriteAllText(alarmFilePath, json);
            }
            catch { }
        }

        // ==================== JSON 讀取 ====================
        private void LoadAlarms()
        {
            try
            {
                alarmFilePath = Path.Combine(Application.StartupPath, ALARM_FILE);
                if (File.Exists(alarmFilePath))
                {
                    string json = File.ReadAllText(alarmFilePath);
                    alarms = JsonSerializer.Deserialize<List<AlarmItem>>(json) ?? new List<AlarmItem>();
                }
            }
            catch { alarms = new List<AlarmItem>(); }

            RefreshListView();
        }
    }
}
