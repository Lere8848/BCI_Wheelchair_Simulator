using System.Collections.Generic;
using UnityEngine;
using Simulator.Logging;


// Note: Input is actually completed on the ROS2 side, Unity just receives commands from ROS2 for simulation.
// Therefore, the Unity-side Logger should not include this.
// However, for testing convenience, this Logger is retained.
// In the future, input recording should be completed on the ROS2 side.
namespace Simulator.LoggingModules
{
    public class InputLogger : MonoBehaviour, ILoggingProvider
    {
        [Header("Input Logger Settings")]
        public float windowDuration = 1.0f;

        private List<float> inputTimestamps = new List<float>();
        private string lastKeyPressed = "";
        private float lastInputTime = -999f;

        private string currentDirection = "";
        private int isInputting = 0;

        public string GetHeader()
        {
            // user_input_key: the key pressed by the user (W, A, S, D, or Other)
            // input_count_window: number of inputs in the last windowDuration seconds
            // is_inputting: 1 if the user is currently pressing a key, 0 otherwise
            // time_since_last_input: time in seconds since the last input was registered
            // input_direction: the direction of the input (e.g., "+x", "-x", "+z", "-z", or "")
            return "user_input_key,input_count_window,is_inputting,time_since_last_input,input_direction";
        }

        public string GetLogLine()
        {
            float now = Time.time;
            inputTimestamps.RemoveAll(t => now - t > windowDuration);

            float timeSinceLastInput = (lastInputTime < 0) ? -1f : now - lastInputTime;

            return $"{lastKeyPressed},{inputTimestamps.Count},{isInputting},{timeSinceLastInput:F3},{currentDirection}";
        }

        void Update()
        {
            isInputting = 0;
            lastKeyPressed = "";
            currentDirection = "";

            if (Input.GetKeyDown(KeyCode.W)) HandleInput("W", "+z");
            else if (Input.GetKeyDown(KeyCode.S)) HandleInput("S", "-z");
            else if (Input.GetKeyDown(KeyCode.A)) HandleInput("A", "-x");
            else if (Input.GetKeyDown(KeyCode.D)) HandleInput("D", "+x");
            else if (Input.anyKeyDown) HandleInput("Other", "");
        }

        private void HandleInput(string key, string direction)
        {
            lastKeyPressed = key;
            currentDirection = direction;
            isInputting = 1;
            lastInputTime = Time.time;
            inputTimestamps.Add(Time.time);
        }
    }
}
