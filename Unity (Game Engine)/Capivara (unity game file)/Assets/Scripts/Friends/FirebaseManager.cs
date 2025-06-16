// FirebaseManager.cs
using UnityEngine;
using Firebase;
using Firebase.Database;
using Firebase.Extensions;
using System;

public class FirebaseManager : MonoBehaviour
{
    public static FirebaseManager Instance;
    private DatabaseReference dbReference;

    public static event Action<string, int> OnMatchmakingSuccess;

    void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }
        else
        {
            Destroy(gameObject);
            return;
        }

        FirebaseApp.CheckAndFixDependenciesAsync().ContinueWithOnMainThread(task => {
            if (task.Exception != null)
            {
                Debug.LogError($"Falha ao inicializar o Firebase: {task.Exception}");
                return;
            }
            dbReference = FirebaseDatabase.DefaultInstance.RootReference;
            Debug.Log("Firebase inicializado com sucesso.");
        });
    }

    public void FindOrCreateRoom(string roomId)
    {
        if (dbReference == null) {
            Debug.LogError("Referência do Banco de Dados está nula.");
            return;
        }

        string deviceId = SystemInfo.deviceUniqueIdentifier;
        DatabaseReference roomRef = dbReference.Child("game_rooms").Child(roomId);

        roomRef.GetValueAsync().ContinueWithOnMainThread(task => {
            if (task.IsFaulted) { return; }

            DataSnapshot snapshot = task.Result;
            if (!snapshot.Exists)
            {
                Debug.Log($"Sala '{roomId}' não encontrada. Criando nova sala...");
                // Cria os dados iniciais do jogador 1
                roomRef.Child("player1").SetValueAsync(deviceId);
                roomRef.Child("status").SetValueAsync("waiting");
                roomRef.Child("player1_data").Child("posY").SetValueAsync(0);
                roomRef.Child("player1_data").Child("score").SetValueAsync(0);
                roomRef.Child("player1_data").Child("isAlive").SetValueAsync(true);
                ListenForPlayer2(roomRef, roomId);
            }
            else
            {
                if (snapshot.HasChild("player2")) { return; }

                Debug.Log($"Entrando na sala '{roomId}' como Jogador 2.");
                // Cria os dados iniciais do jogador 2
                roomRef.Child("player2").SetValueAsync(deviceId);
                roomRef.Child("status").SetValueAsync("ready");
                roomRef.Child("player2_data").Child("posY").SetValueAsync(0);
                roomRef.Child("player2_data").Child("score").SetValueAsync(0);
                roomRef.Child("player2_data").Child("isAlive").SetValueAsync(true);
                
                OnMatchmakingSuccess?.Invoke(roomId, 2);
            }
        });
    }

    private void ListenForPlayer2(DatabaseReference roomRef, string roomId)
    {
        roomRef.Child("status").ValueChanged += HandleStatusChanged;
        void HandleStatusChanged(object sender, ValueChangedEventArgs args)
        {
            if (args.Snapshot != null && args.Snapshot.Value.ToString() == "ready")
            {
                OnMatchmakingSuccess?.Invoke(roomId, 1);
                roomRef.Child("status").ValueChanged -= HandleStatusChanged;
            }
        }
    }

    // --- NOVAS FUNÇÕES DE SINCRONIZAÇÃO ---
    private DatabaseReference GetPlayerRef()
    {
        if (GameSession.RoomId == null) return null;
        string playerNode = GameSession.PlayerNumber == 1 ? "player1_data" : "player2_data";
        return dbReference.Child("game_rooms").Child(GameSession.RoomId).Child(playerNode);
    }
    
    public void UpdatePlayerPosition(float posY)
    {
        GetPlayerRef()?.Child("posY").SetValueAsync(posY);
    }

    public void UpdatePlayerScore(int score)
    {
        GetPlayerRef()?.Child("score").SetValueAsync(score);
    }

    public void UpdatePlayerStatus(bool isAlive)
    {
        GetPlayerRef()?.Child("isAlive").SetValueAsync(isAlive);
    }
}