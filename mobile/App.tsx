import { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, Image,
  ScrollView, ActivityIndicator, StyleSheet, Alert,
} from 'react-native'
import * as MediaLibrary from 'expo-media-library'
import * as FileSystem from 'expo-file-system'

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? ''

interface Result {
  original_url: string
  processed_image: string
  claude_pass_applied: boolean
  is_carousel: boolean
}

export default function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [error, setError] = useState('')

  async function handleSubmit() {
    if (!url.trim()) return
    setLoading(true)
    setResult(null)
    setError('')
    try {
      const res = await fetch(`${API_URL}/defilter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail ?? 'Something went wrong')
      } else {
        setResult(data)
      }
    } catch {
      setError('Could not reach the server')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave() {
    if (!result) return
    const { status } = await MediaLibrary.requestPermissionsAsync()
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Allow access to save photos.')
      return
    }
    const path = `${FileSystem.cacheDirectory}defiltered.png`
    await FileSystem.writeAsStringAsync(path, result.processed_image, {
      encoding: FileSystem.EncodingType.Base64,
    })
    await MediaLibrary.saveToLibraryAsync(path)
    Alert.alert('Saved', 'De-filtered image saved to camera roll.')
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Instagram De-Filter</Text>
      <Text style={styles.subtitle}>Paste an Instagram post URL</Text>

      <TextInput
        style={styles.input}
        value={url}
        onChangeText={setUrl}
        placeholder="https://www.instagram.com/p/..."
        autoCapitalize="none"
        keyboardType="url"
      />

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={loading}
      >
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.buttonText}>De-filter</Text>}
      </TouchableOpacity>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {result && (
        <View style={styles.results}>
          <View style={styles.imageRow}>
            <View style={styles.imageCol}>
              <Text style={styles.label}>ORIGINAL</Text>
              <Image source={{ uri: result.original_url }} style={styles.image} />
            </View>
            <View style={styles.imageCol}>
              <Text style={styles.label}>DE-FILTERED</Text>
              <Image
                source={{ uri: `data:image/png;base64,${result.processed_image}` }}
                style={styles.image}
              />
            </View>
          </View>
          {result.is_carousel && (
            <Text style={styles.carouselNote}>Only the first image was processed (carousel post)</Text>
          )}
          <TouchableOpacity style={styles.saveButton} onPress={handleSave}>
            <Text style={styles.saveText}>Save to Camera Roll</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, padding: 20, paddingTop: 60, backgroundColor: '#f9f9f9' },
  title: { fontSize: 24, fontWeight: 'bold', color: '#111', marginBottom: 4 },
  subtitle: { fontSize: 14, color: '#888', marginBottom: 20 },
  input: {
    borderWidth: 1, borderColor: '#ddd', borderRadius: 10,
    paddingHorizontal: 14, paddingVertical: 10, fontSize: 14,
    backgroundColor: '#fff', marginBottom: 12,
  },
  button: {
    backgroundColor: '#2563eb', borderRadius: 10, paddingVertical: 12,
    alignItems: 'center', marginBottom: 12,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 15 },
  error: { color: '#dc2626', fontSize: 13, marginBottom: 12 },
  results: { marginTop: 8 },
  imageRow: { flexDirection: 'row', gap: 8 },
  imageCol: { flex: 1 },
  label: { fontSize: 10, fontWeight: '700', color: '#888', marginBottom: 4, letterSpacing: 1 },
  image: { width: '100%', aspectRatio: 1, borderRadius: 8, backgroundColor: '#eee' },
  carouselNote: { fontSize: 12, color: '#d97706', marginTop: 8 },
  saveButton: { marginTop: 12, padding: 12, backgroundColor: '#f0f0f0', borderRadius: 10, alignItems: 'center' },
  saveText: { fontSize: 14, color: '#2563eb', fontWeight: '600' },
})
