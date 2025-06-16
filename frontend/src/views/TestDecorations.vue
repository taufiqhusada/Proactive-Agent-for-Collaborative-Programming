<template>
    <div class="container mt-4">
        <h3>CodeMirror Decoration Test</h3>
        <button class="btn btn-primary mb-3" @click="testDecoration">
            Test Decoration
        </button>
        <div style="border: 1px solid #ccc; border-radius: 4px;">
            <codemirror 
                v-model="code" 
                :style="{ height: '300px' }" 
                :extensions="extensions"
                @ready="handleReady" 
            />
        </div>
    </div>
</template>

<script>
import { defineComponent, ref } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'
import { StateField, StateEffect } from '@codemirror/state'
import { EditorView, Decoration } from '@codemirror/view'

export default defineComponent({
    components: {
        Codemirror,
    },

    setup() {
        const code = ref('print("Hello World")\nprint("Test decoration")\nprint("Another line")')
        const view = ref(null)

        // Define effects
        const addDecoration = StateEffect.define()
        
        // Define state field
        const decorationField = StateField.define({
            create() {
                return Decoration.none
            },
            update(decorations, tr) {
                decorations = decorations.map(tr.changes)
                
                for (let effect of tr.effects) {
                    if (effect.is(addDecoration)) {
                        const { from, to, className } = effect.value
                        console.log('Adding decoration from', from, 'to', to, 'with class', className)
                        
                        decorations = decorations.update({
                            add: [
                                Decoration.mark({
                                    class: className
                                }).range(from, to)
                            ]
                        })
                    }
                }
                
                return decorations
            },
            provide: f => EditorView.decorations.from(f)
        })

        const extensions = [
            python(),
            oneDark,
            decorationField
        ]

        const handleReady = (payload) => {
            view.value = payload.view
            console.log('CodeMirror ready, view:', view.value)
        }

        const testDecoration = () => {
            console.log('Test decoration clicked, view:', view.value)
            
            if (view.value) {
                console.log('Dispatching decoration effect')
                
                view.value.dispatch({
                    effects: [addDecoration.of({
                        from: 0,
                        to: 5,
                        className: 'test-highlight'
                    })]
                })
                
                console.log('Effect dispatched')
            } else {
                console.error('View is not available!')
            }
        }

        return {
            code,
            extensions,
            handleReady,
            testDecoration
        }
    }
})
</script>

<style>
.test-highlight {
    background-color: rgba(255, 255, 0, 0.5) !important;
    border-radius: 3px;
}
</style>
