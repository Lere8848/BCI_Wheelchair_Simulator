namespace Simulator.LoggingModules
{
    public interface ILoggingProvider
    {
        string GetHeader();      // Header
        string GetLogLine();     // data
    }
}
