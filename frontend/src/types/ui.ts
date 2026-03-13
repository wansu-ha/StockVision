/** UI 관련 타입 */

export type TrafficLightColor = 'green' | 'red' | 'yellow'

export interface ServerStatus {
  cloud: TrafficLightColor
  local: TrafficLightColor
  broker: TrafficLightColor
  cloud_message?: string
  local_message?: string
  broker_message?: string
}

export type AlertType = 'info' | 'success' | 'warning' | 'error'

export interface AlertItem {
  id: number
  type: AlertType
  message: string
  timestamp: number
}
