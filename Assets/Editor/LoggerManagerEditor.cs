#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using Simulator.Logging;

// to test if the LoggerManager runs correctly
[CustomEditor(typeof(LoggerManager))]
public class LoggerManagerEditor : Editor
{
    public override void OnInspectorGUI()
    {
        DrawDefaultInspector();

        LoggerManager logger = (LoggerManager)target;

        GUILayout.Space(10);
        GUILayout.Label("Logger Controls (Test only)", EditorStyles.boldLabel);

        if (GUILayout.Button("Start Logging"))
        {
            logger.StartLogging();
        }

        if (GUILayout.Button("Stop Logging"))
        {
            logger.StopLogging();
        }
    }
}
#endif
