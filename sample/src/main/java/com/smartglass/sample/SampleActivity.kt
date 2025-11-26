package com.smartglass.sample

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.smartglass.sdk.SmartGlassClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class SampleActivity : AppCompatActivity() {

    private lateinit var promptInput: EditText
    private lateinit var responseText: TextView

    private val client = SmartGlassClient()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_sample)

        promptInput = findViewById(R.id.promptInput)
        responseText = findViewById(R.id.responseText)

        findViewById<Button>(R.id.sendButton).setOnClickListener {
            sendPrompt()
        }
    }

    private fun sendPrompt() {
        val prompt = promptInput.text.toString()
        if (prompt.isBlank()) {
            Toast.makeText(this, R.string.prompt_required, Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch {
            setStatus(getString(R.string.starting_session))
            try {
                // Stubbed image handling for now; only text is sent.
                val sessionId = client.startSession(text = prompt)
                val response = client.answer(sessionId = sessionId, text = prompt)

                val actionsSummary = response.actions.takeIf { it.isNotEmpty() }
                    ?.joinToString(prefix = "\nActions:\n", separator = "\n") { action ->
                        "• ${action.type}: ${action.payload}"
                    } ?: ""

                val responseSummary = buildString {
                    append(getString(R.string.response_prefix, response.response))
                    if (actionsSummary.isNotBlank()) append(actionsSummary)
                }

                setStatus(responseSummary)
            } catch (exc: Exception) {
                setStatus(getString(R.string.response_error, exc.message))
            }
        }
    }

    private suspend fun setStatus(message: String) {
        withContext(Dispatchers.Main) {
            responseText.text = message
            Toast.makeText(this@SampleActivity, message, Toast.LENGTH_SHORT).show()
        }
    }
}
