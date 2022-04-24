using Newtonsoft.Json.Linq;
using Serilog;

namespace FortnitePorting;

public static class Benbot
{
    private static readonly HttpClient _httpClient = new()
    {
        Timeout = TimeSpan.FromSeconds(2), 
        DefaultRequestHeaders = {{ "User-Agent", "FortnitePorting" }}
    };
    
    public static string GetCosmeticPath(string input, string backendType)
    {
        var requestUri = $"https://benbot.app/api/v1/cosmetics/br/search/all?&name={input}&backendType={backendType}";
        var response = _httpClient.GetAsync(requestUri).Result;

        var responseString = response.Content.ReadAsStringAsync().Result;
        var json = JArray.Parse(responseString);

        return json[0]["path"].ToString();
    }

}