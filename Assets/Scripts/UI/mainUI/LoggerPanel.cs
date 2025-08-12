using UnityEngine;
using TMPro;
using Simulator.Logging;

public class LoggerControlUI : MonoBehaviour
{
    public TMP_Text loggingStatusText;
    private LoggerManager logger;
    private enum LoggingState { Idle, Recording, Stopped }
    private LoggingState currentState = LoggingState.Idle;

    void Start()
    {
        logger = FindAnyObjectByType<LoggerManager>();
        if (logger == null)
            Debug.LogError("LoggerManager not found in scene.");
        
        // Initialize logging status
        currentState = LoggingState.Idle;
        UpdateStatus();
    }

    public void StartLogging()
    {
        if (logger == null) return;

        logger.StartLogging();
        currentState = LoggingState.Recording;
        UpdateStatus();
    }

    public void StopLogging()
    {
        if (logger == null) return;

        logger.StopLogging();
        currentState = LoggingState.Stopped;
        UpdateStatus();
    }

    private void UpdateStatus()
    {
        if (logger == null) return;

        switch (currentState)
        {
            case LoggingState.Idle:
                loggingStatusText.text = "log status: ";
                break;
            case LoggingState.Recording:
                loggingStatusText.text = "log status: Recording";
                break;
            case LoggingState.Stopped:
                loggingStatusText.text = "log status: Not Recording";
                break;
        }
    }
}