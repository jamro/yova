#!/bin/bash

# Supervisor Manager Script for YOVA
# This script helps manage supervisor processes

CONFIG_FILE="configs/supervisord.conf"
SUPERVISOR_CMD="poetry run supervisord"
SUPERVISORCTL_CMD="poetry run supervisorctl"

# Function to check if supervisor is running
is_supervisor_running() {
    if [ -f "/tmp/supervisord.pid" ]; then
        pid=$(cat /tmp/supervisord.pid)
        if ps -p $pid > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to start supervisor
start_supervisor() {
    echo "Starting supervisor..."
    if is_supervisor_running; then
        echo "Supervisor is already running (PID: $(cat /tmp/supervisord.pid))"
        return 0
    fi
    
    $SUPERVISOR_CMD -c $CONFIG_FILE
    sleep 2
    
    if is_supervisor_running; then
        echo "Supervisor started successfully (PID: $(cat /tmp/supervisord.pid))"
        echo "Checking process status..."
        $SUPERVISORCTL_CMD -c $CONFIG_FILE status
    else
        echo "Failed to start supervisor"
        return 1
    fi
}

# Function to stop supervisor
stop_supervisor() {
    echo "Stopping supervisor..."
    if ! is_supervisor_running; then
        echo "Supervisor is not running"
        return 0
    fi
    
    $SUPERVISORCTL_CMD -c $CONFIG_FILE shutdown
    sleep 2
    
    if ! is_supervisor_running; then
        echo "Supervisor stopped successfully"
    else
        echo "Failed to stop supervisor"
        return 1
    fi
}

# Function to restart yova_core
restart_yova() {
    echo "Restarting yova_core..."
    if ! is_supervisor_running; then
        echo "Supervisor is not running. Starting it first..."
        start_supervisor
    fi
    
    $SUPERVISORCTL_CMD -c $CONFIG_FILE restart yova_core
    echo "yova_core restart initiated"
}

# Function to show status
show_status() {
    if ! is_supervisor_running; then
        echo "Supervisor is not running"
        return 1
    fi
    
    echo "Supervisor Status:"
    echo "=================="
    $SUPERVISORCTL_CMD -c $CONFIG_FILE status
}

# Function to show logs
show_logs() {
    if ! is_supervisor_running; then
        echo "Supervisor is not running"
        return 1
    fi
    
    echo "yova_core logs:"
    echo "==============="
    $SUPERVISORCTL_CMD -c $CONFIG_FILE tail yova_core
}

# Function to follow logs
follow_logs() {
    if ! is_supervisor_running; then
        echo "Supervisor is not running"
        return 1
    fi
    
    echo "Following yova_core logs (Ctrl+C to stop):"
    echo "=========================================="
    $SUPERVISORCTL_CMD -c $CONFIG_FILE tail -f yova_core
}

# Function to show help
show_help() {
    echo "YOVA Supervisor Manager"
    echo "======================="
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start supervisor and yova_core process"
    echo "  stop      Stop supervisor and all processes"
    echo "  restart   Restart yova_core process"
    echo "  status    Show status of all supervised processes"
    echo "  logs      Show yova_core logs"
    echo "  follow    Follow yova_core logs in real-time"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 status"
    echo "  $0 logs"
}

# Main script logic
case "${1:-help}" in
    start)
        start_supervisor
        ;;
    stop)
        stop_supervisor
        ;;
    restart)
        restart_yova
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    follow)
        follow_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
