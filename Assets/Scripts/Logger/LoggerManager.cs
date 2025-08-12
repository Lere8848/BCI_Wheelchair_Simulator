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
            // automatically register all ILoggingProvider modules in the scene
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

            // Create log file path
            string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            // Create Logs directory (if it doesn't exist) under Application.dataPath
            // eg: Assets/Logs/log_20250624_123456.csv
            string logsDirectory = Path.Combine(Application.dataPath, "Logs");
            if (!Directory.Exists(logsDirectory))
                Directory.CreateDirectory(logsDirectory);
                
            logFilePath = Path.Combine(logsDirectory, $"log_{timestamp}.csv");
            writer = new StreamWriter(logFilePath);

            // Write CSV header
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
