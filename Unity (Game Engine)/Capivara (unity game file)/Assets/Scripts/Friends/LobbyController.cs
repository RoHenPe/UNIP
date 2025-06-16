// LobbyController.cs
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.SceneManagement;
using System.Collections;

public class LobbyController : MonoBehaviour
{
    [SerializeField] private InputField roomIdField;
    [SerializeField] private Button findMatchButton;
    
    // --- LINHA CORRIGIDA ---
    [SerializeField] private string multiplayerSceneName = "Multiplay";

    private Coroutine pulseCoroutine;

    void OnEnable()
    {
        FirebaseManager.OnMatchmakingSuccess += HandleMatchmakingSuccess;
    }

    void OnDisable()
    {
        FirebaseManager.OnMatchmakingSuccess -= HandleMatchmakingSuccess;
    }

    public void OnFindMatchClicked()
    {
        string roomId = roomIdField.text;
        if (string.IsNullOrEmpty(roomId))
        {
            Debug.LogWarning("O ID da sala não pode ser vazio.");
            return;
        }

        findMatchButton.interactable = false;
        pulseCoroutine = StartCoroutine(PulseButton());

        FirebaseManager.Instance.FindOrCreateRoom(roomId);
    }

    private void HandleMatchmakingSuccess(string roomId, int playerNumber)
    {
        Debug.Log($"Sucesso! Entrando na sala {roomId} como Jogador {playerNumber}");
        
        GameSession.RoomId = roomId;
        GameSession.PlayerNumber = playerNumber;

        if (pulseCoroutine != null)
        {
            StopCoroutine(pulseCoroutine);
        }
        SceneManager.LoadScene(multiplayerSceneName);
    }

    private IEnumerator PulseButton()
    {
        RectTransform buttonRect = findMatchButton.GetComponent<RectTransform>();
        float originalScale = 1f;
        float pulseScale = 1.05f;
        float speed = 2.5f;

        while (true)
        {
            float scale = Mathf.PingPong(Time.time * speed, pulseScale - originalScale) + originalScale;
            buttonRect.localScale = new Vector3(scale, scale, 1f);
            yield return null;
        }
    }
}