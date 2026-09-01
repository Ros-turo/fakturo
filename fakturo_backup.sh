#!/bin/bash

# Script control if docker conteiners is running
# After that backup db with timestamp in filename
# Log 
# Clean up old backups
# Resume how much backups exist, files size etc.

ENVIRONMENT="dev"
VERBOSE=false
CONTAINER_NAME="db"
DB_USER="${DB_USER:-fakturo_user}"
DB_NAME="${DB_NAME:-fakturo_db}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/sandbox/backups}"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
RETENTION_DAYS=${RETENTION_DAYS:-7}

func_checker(){	
	if [ "$?" -ne 0 ]; then
		exit 1
	fi
}

check_prerequisites(){
	docker info > /dev/null 2>&1
	if [  "$?" -ne 0 ]; then
		echo "Docker is not active"
		return 1
	fi
	
	conteiner_id=$(docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" -q)
	
	if [ -z "$conteiner_id" ]; then
		echo "Container $CONTAINER_NAME nebezi"
		return 1
	fi
	if [ "$VERBOSE" = true ]; then
		echo "Docker is active;"
		echo "Container $CONTAINER_NAME is running"
	fi
	return 0
}

perform_backup(){
	mkdir -p "$BACKUP_DIR"
	backup_file="$BACKUP_DIR/fakturo_backup_${TIMESTAMP}.sql"
	docker exec "$conteiner_id" pg_dump -U "$DB_USER" "$DB_NAME" > "$backup_file"
	
	if [ "$?" -ne 0 ]; then
		echo "Data extract error"
		return 1
	fi 

	if [ "$VERBOSE" = true ];then
		echo "Backup created: $backup_file"
	fi

	return 0
}
cleanup_old_backups(){
	local backups_count=$(find "$BACKUP_DIR" -name "fakturo_backup_*.sql" -mtime +"$RETENTION_DAYS" | wc -l)
	if [[ $backups_count -gt 0 && "$VERBOSE" = true ]]; then
		echo "Clean up $backups_count files (old than $RETENTION_DAYS)"
	fi

	find "$BACKUP_DIR" -name "fakturo_backup_*.sql" -mtime +"$RETENTION_DAYS" -delete
	return 0
	
}

while getopts "e:vh" opt; do
  case "$opt" in
    e)
	case "$OPTARG" in
	"dev"|"staging"|"prod") ENVIRONMENT="$OPTARG";;
	*) echo "-e flag has this arguments: dev, staging, prod "
		exit 1
	esac
	;;
    v)
	VERBOSE=true;;
    h)
	echo "Pouziti: ./fakturo_backup "
	exit 0;;
  esac
done

shift $((OPTIND-1))

check_prerequisites
func_checker

perform_backup
func_checker

cleanup_old_backups
