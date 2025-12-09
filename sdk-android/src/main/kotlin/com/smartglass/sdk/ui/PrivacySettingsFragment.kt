package com.smartglass.sdk.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Switch
import android.widget.TextView
import androidx.fragment.app.Fragment
import com.smartglass.sdk.PrivacyPreferences

/**
 * Privacy settings screen for SmartGlass data storage controls.
 *
 * This fragment provides user-facing toggles for controlling what data the backend
 * is allowed to temporarily store during a session. All storage is in-memory only.
 *
 * The glasses are accessed via Meta's Wearables Device Access Toolkit preview,
 * which provides camera and audio streaming capabilities. Users can stop streaming
 * at any time by disconnecting or stopping the session.
 */
class PrivacySettingsFragment : Fragment() {

    private lateinit var audioSwitch: Switch
    private lateinit var framesSwitch: Switch
    private lateinit var transcriptsSwitch: Switch

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_privacy_settings, container, false)

        audioSwitch = view.findViewById(R.id.switchStoreAudio)
        framesSwitch = view.findViewById(R.id.switchStoreFrames)
        transcriptsSwitch = view.findViewById(R.id.switchStoreTranscripts)

        // Load current preferences
        val prefs = PrivacyPreferences.load(requireContext())
        audioSwitch.isChecked = prefs.storeRawAudio
        framesSwitch.isChecked = prefs.storeRawFrames
        transcriptsSwitch.isChecked = prefs.storeTranscripts

        // Set up listeners to save on change
        audioSwitch.setOnCheckedChangeListener { _, _ -> savePreferences() }
        framesSwitch.setOnCheckedChangeListener { _, _ -> savePreferences() }
        transcriptsSwitch.setOnCheckedChangeListener { _, _ -> savePreferences() }

        return view
    }

    private fun savePreferences() {
        val prefs = PrivacyPreferences(
            storeRawAudio = audioSwitch.isChecked,
            storeRawFrames = framesSwitch.isChecked,
            storeTranscripts = transcriptsSwitch.isChecked,
        )
        PrivacyPreferences.save(requireContext(), prefs)
    }
}
