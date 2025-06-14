using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

public class PularCena : MonoBehaviour
{
    public void CarregarCena(string Simple)
    {
        SceneManager.LoadScene(Simple);
    }
}
