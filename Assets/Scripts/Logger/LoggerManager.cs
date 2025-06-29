using System.Collections.Generic;
using System.IO;
using UnityEngine;
using System;
using Simulator.LoggingModules;

namespace Simulator.Logging
{
    public class LoggerManager : MonoBehaviour
    {
        public float logFrequencyHz = 10f;
        private float logInterval => 1f / logFrequencyHz;
        private float timer = 0f;
        private bool isLogging = false;

        private string logFilePath;
        private StreamWriter writer;

        private List<ILoggingProvider> providers = new List<ILoggingProvider>();

        void Start()
        {
            // 自动注册场景中所有继承了 ILoggingProvider 的模块
            foreach (var provider in FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None))
            {
                if (provider is ILoggingProvider loggingProvider)
                    providers.Add(loggingProvider);
            }
        }

        void Update()
        {
            if (!isLogging) return;

            timer += Time.deltaTime;
            if (timer >= logInterval)
            {
                timer = 0f;
                WriteLogLine();
            }
        }

        public void StartLogging()
        {
            if (isLogging) return;

            // 创建日志文件路径
            string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            // 创建Logs目录(如果不存在) 保存在 Application.dataPath 下的 Logs 文件夹
            // eg: Assets/Logs/log_20250624_123456.csv
            string logsDirectory = Path.Combine(Application.dataPath, "Logs");
            if (!Directory.Exists(logsDirectory))
                Directory.CreateDirectory(logsDirectory);
                
            logFilePath = Path.Combine(logsDirectory, $"log_{timestamp}.csv");
            writer = new StreamWriter(logFilePath);

            // 写入 CSV 头部
            List<string> headers = new List<string> { "timestamp" };
            foreach (var p in providers)
                headers.Add(p.GetHeader());

            writer.WriteLine(string.Join(",", headers));
            isLogging = true;

            Debug.Log($"[LoggerManager] Logging started: {logFilePath}");
        }

        public void StopLogging()
        {
            if (!isLogging) return;

            isLogging = false;
            writer?.Close();
            Debug.Log($"[LoggerManager] Logging stopped. Log saved to: {logFilePath}");
        }

        private void WriteLogLine()
        {
            List<string> values = new List<string> { Time.time.ToString("F3") };
            foreach (var p in providers)
                values.Add(p.GetLogLine());

            writer.WriteLine(string.Join(",", values));
        }
    }
}
