using Serilog;

namespace FortnitePorting;

public static class Benbot
{
    private static HttpClient _httpClient = new()
    {
        Timeout = TimeSpan.FromSeconds(2), 
        DefaultRequestHeaders = {{ "User-Agent", "FortnitePorting" }}
    };
    
    public static void GetCosmeticPath(string input, string backendType)
    {
        var requestUri = $"https://benbot.app/api/v1/cosmetics/br/search/all?&name={input}&backendType={backendType}";
        var response = _httpClient.GetAsync(requestUri).Result;
        Log.Information(response.Content.ToString());
    }

}